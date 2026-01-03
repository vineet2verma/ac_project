import random
import string

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from cnc_work_app.mongo import users_collection
from bson import ObjectId


def logout_view(request):
    request.session.flush()
    return redirect("accounts_app:login")

# @login_required
# @role_required(["ADMIN"])
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
            "role": "STAFF",     # 🔒 Admin controlled
            "is_active": True,
        })

        messages.success(request, "Account created successfully. Please login.")
        return redirect("accounts_app:login")

    return render(request, "accounts_app/signup.html")

# @login_required
# @role_required(["ADMIN"])
def user_master(request):
    users_col = users_collection()
    users = list(users_col.find())

    ROLE_CHOICES = [
        "ADMIN",
        "MANAGER",
        "SALES",
        "PRODUCTION",
        "DISPATCH",
        "DESIGNER"
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


# @login_required
# @role_required(["ADMIN"])
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

def forgot_password(request):
    if request.method == "POST":
        messages.success(
            request,
            "If this user exists, the admin will reset the password."
        )

    return render(
        request,
        "accounts_app/forgot_password.html"
    )

def generate_temp_password(length=8):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def reset_password(request, user_id):
    users_col = users_collection()
    temp_password = generate_temp_password()
    result = users_col.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "password": make_password(temp_password),
            "force_password_change": True
        }}
    )

    if result.modified_count == 1:
        messages.success(
            request,
            f"Password reset successfully. Temporary password: {temp_password}"
        )
    else:
        messages.error(
            request,
            "Unable to reset password. User not found."
        )

    return redirect("accounts_app:user_master")


def mongo_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("mongo_user_id"):
            return redirect("accounts_app:login")
        return view_func(request, *args, **kwargs)
    return wrapper

def mongo_role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            role = request.session.get("mongo_role")
            if role not in allowed_roles:
                return redirect("accounts_app:login")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = users_collection().find_one({
            "username": username,
            "is_active": True
        })

        if user and check_password(password, user["password"]):
            # 🔐 manual session
            request.session["mongo_user_id"] = str(user["_id"])
            request.session["mongo_role"] = user["role"]
            request.session["mongo_username"] = user["username"]

            # 🎯 ROLE BASED REDIRECT
            if user["role"] in ["ADMIN", "MANAGER"]:
                return redirect("core_app:dashboard")

            elif user["role"] == "SALES":
                return redirect("cnc_work_app:index")

            else:
                # fallback (optional)
                return redirect("accounts_app:login")

        return render(request, "accounts_app/login.html", {
            "error": "Invalid credentials"
        })

    return render(request, "accounts_app/login.html")

