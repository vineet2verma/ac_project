import random
import string

from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from cnc_work_app.mongo import users_collection
from bson import ObjectId

def mongo_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("mongo_user_id"):
            return redirect("accounts_app:login")
        return view_func(request, *args, **kwargs)
    return wrapper

def mongo_role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            roles = request.session.get("mongo_roles", [])

            # ✅ MULTI ROLE MATCH
            if not any(role in allowed_roles for role in roles):
                messages.error(request, "Permission denied")
                return redirect("accounts_app:login")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def signup_view(request):
    if request.method == "POST":
        data = {
            "full_name": request.POST.get("full_name"),
            "username": request.POST.get("username"),
            "dob": request.POST.get("dob"),
            "mobile": request.POST.get("mobile"),
            "department": request.POST.get("department"),
            "password": request.POST.get("password"),
            "confirm_password": request.POST.get("confirm_password"),
        }

        if data["password"] != data["confirm_password"]:
            messages.error(request, "Passwords do not match")
            return redirect("accounts_app:signup")

        users_col = users_collection()
        if users_col.find_one({"username": data["username"]}):
            messages.error(request, "Username already exists")
            return redirect("accounts_app:signup")

        users_col.insert_one({
            "full_name": data["full_name"],
            "username": data["username"],
            "dob": data["dob"],
            "mobile": data["mobile"],
            "department": data["department"],
            "password": make_password(data["password"]),
            "roles" : [],
            "is_active": True,
        })

        messages.success(request, "Account created successfully. Please login.")
        return redirect("accounts_app:login")

    return render(request, "accounts_app/signup.html")

def forgot_password(request):
    if request.method == "POST":
        messages.success(request,"If this user exists, the admin will reset the password.")
    return render(request,"accounts_app/forgot_password.html")

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = users_collection().find_one({
            "username": username,
            "is_active": True
        })

        print(f"user: {user} password: {password}")

        # ❌ Invalid username or password
        if not user or not check_password(password, user.get("password")):
            messages.error(request, "Invalid username or password.")
            return render(request, "accounts_app/login.html")

        # ✅ Login success – set session
        roles = user.get("roles", [])

        request.session["mongo_user_id"] = str(user["_id"])
        request.session["mongo_username"] = user["username"]
        request.session["mongo_roles"] = roles

        # 🎯 ROLE BASED REDIRECT ( MULTI ROLE LOGIN )
        if not roles:
            messages.error(
                request,
                "Your role is not defined. Please contact the administrator."
            )
            return redirect("accounts_app:role_not_defined")

        if "ADMIN" in roles:
            return redirect("core_app:dashboard")

        return redirect("cnc_work_app:index")

    return render(request, "accounts_app/login.html")



def role_not_defined(request):
    return render(request,"accounts_app/role_not_defined.html",{"year": datetime.now().year})


@mongo_login_required
def logout_view(request):
    request.session.flush()
    return redirect("accounts_app:login")

@mongo_login_required
@mongo_role_required(["ADMIN"])
def user_master(request):
    users_col = users_collection()
    users = list(users_col.find())

    ROLE_CHOICES = [
        "ADMIN",
        "MANAGER",
        "DASHBOARD",
        "REPORT",
        "SALES",
        "DESIGNER",
        "PRODUCTION",
        "INVENTORY",
        "QC",
        "DISPATCH",
    ]

    for u in users:
        u["id"] = str(u["_id"])
        u["roles"] = u.get("roles", [])

    return render(
        request,
        "accounts_app/user_master.html",
        {
            "users": users,
            "ROLE_CHOICES": ROLE_CHOICES
        }
    )

@mongo_login_required
@mongo_role_required(["ADMIN"])
def update_user(request, user_id):
    if request.method == "POST":
        users_col = users_collection()

        roles = request.POST.getlist("roles")  # ✅ MULTIPLE ROLES

        if not roles:
            messages.error(request, "At least one role is required.")
            return redirect("accounts_app:user_master")

        users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "full_name": request.POST.get("full_name"),
                "dob": request.POST.get("dob") or None,
                "mobile": request.POST.get("mobile"),
                "department": request.POST.get("department"),
                "roles": roles,
                "is_active": request.POST.get("is_active") == "true"
            }}
        )

        messages.success(request, "User updated successfully")

    return redirect("accounts_app:user_master")


@mongo_login_required
@mongo_role_required(["ADMIN"])
def generate_temp_password(length=8):
    print("Generate Temp Clicked")
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


@mongo_login_required
@mongo_role_required(["ADMIN"])
def admin_reset_password(request, user_id):

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("accounts_app:user_master")  # ✅ FIXED

        users_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": make_password(new_password)}}
        )

        messages.success(request, "Password reset successfully")

    return redirect("accounts_app:user_master")  # ✅ FIXED

