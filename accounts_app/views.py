import random
import string
import uuid
from datetime import datetime

from django.contrib.auth.hashers import make_password, check_password
from cnc_work_app.mongo import users_collection, get_login_activity_collection
from bson import ObjectId
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from utils.cookies import set_cookie, delete_cookie

def mongo_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get("mongo_user_id")
        device_id = request.session.get("device_id")

        if not user_id or not device_id:
            return redirect("accounts_app:login")

        user = users_collection().find_one({"_id": ObjectId(user_id)})

        if not user or user.get("active_device_id") != device_id:
            request.session.flush()
            messages.error(request, "You were logged out (new login detected).")
            return redirect("accounts_app:login")

        return view_func(request, *args, **kwargs)
    return wrapper
# def mongo_login_required(view_func):
#     def wrapper(request, *args, **kwargs):
#         if not request.session.get("mongo_user_id"):
#             return redirect("accounts_app:login")
#         return view_func(request, *args, **kwargs)
#     return wrapper

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

def role_not_defined(request):
    return render(request,"accounts_app/role_not_defined.html",{"year": datetime.now().year})

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

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "").strip()
        remember_me = request.POST.get("remember_me")

        user = users_collection().find_one({
            "username": username,
            "is_active": True
        })

        if not user or not check_password(password, user.get("password")):
            messages.error(request, "Invalid username or password")
            return render(request, "accounts_app/login.html")

        # 🔐 SESSION
        request.session["mongo_user_id"] = str(user["_id"])
        request.session["mongo_username"] = user["username"]
        request.session["mongo_roles"] = user.get("roles", [])
        request.session["access_scope"] = user.get("access_scope", "OWN")
        request.session["work_type_access"] = user.get("work_type_access", [])

        # ⏱ SESSION EXPIRY
        if remember_me:
            request.session.set_expiry(60 * 60 * 24 * 7)  # 7 days
        else:
            request.session.set_expiry(0)  # browser close


        # DEVICE ID MUST EXIST FIRST
        device_id = str(uuid.uuid4())
        request.session["device_id"] = device_id

        record_login(request, user)

        response = redirect(
            "core_app:dashboard" if "ADMIN" in user["roles"] else "cnc_work_app:index"
        )

        if remember_me:
            set_cookie(response, "remember_token", str(user["_id"]), days=7)

        return response

    return render(request, "accounts_app/login.html")

# def login_view(request):
#     if request.method == "POST":
#         username = request.POST.get("username", "").strip().lower()
#         password = request.POST.get("password", "").strip()
#
#         user = users_collection().find_one({
#             "username": username,
#             "is_active": True
#         })
#
#         # ❌ Invalid username or password
#         if not user or not check_password(password, user.get("password")):
#             messages.error(request, "Invalid username or password.")
#             return render(request, "accounts_app/login.html")
#
#         # ✅ Login success – set session
#         roles = user.get("roles", [])
#
#         request.session["mongo_user_id"] = str(user["_id"])
#         request.session["mongo_username"] = user["username"]
#         request.session["mongo_roles"] = roles
#         request.session["access_scope"] = user.get("access_scope", "OWN")
#         request.session["work_type_access"] = user.get("work_type_access", [])  # ✅ REQUIRED
#
#         # 🔥 SAVE LOGIN ACTIVITY
#         record_login(request, user)
#
#         # 🎯 ROLE BASED REDIRECT ( MULTI ROLE LOGIN )
#         if not roles:
#             messages.error(
#                 request,
#                 "Your role is not defined. Please contact the administrator."
#             )
#             return redirect("accounts_app:role_not_defined")
#
#         # 🎯 Decide redirect URL
#         if "ADMIN" in roles:
#             redirect_url = "core_app:dashboard"
#         else:
#             redirect_url = "cnc_work_app:index"
#
#         # ✅ Create response FIRST
#         response = redirect(redirect_url)
#
#         # 🍪 SET COOKIES (non-sensitive)
#         set_cookie(response, "username", user["username"], days=7)
#         set_cookie(response, "primary_role", roles[0], days=7)
#
#         return response
#
#     return render(request, "accounts_app/login.html")




@mongo_login_required
def logout_view(request):
    response = redirect("accounts_app:login")
    delete_cookie(response, "username")
    delete_cookie(response, "primary_role")
    record_logout(request)  # 🔥 save logout activity
    request.session.flush()
    return response


@mongo_login_required
@mongo_role_required(["ADMIN","MANAGER"])
def user_master(request):
    users_col = users_collection()

    ROLE_CHOICES = [
        "ADMIN", "MANAGER", "DASHBOARD", "SALES",
        "DESIGNER", "PRODUCTION", "INVENTORY", "QC", "DISPATCH"
    ]

    ACCESS_CHOICES = ["OWN", "ALL"]

    VALID_WORK_TYPES = [
        "CNC Work",
        "Third Fire",
        "Sand Blasting",
        "Tile Cutting",
    ]

    # ================= UPDATE USER =================
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        roles = request.POST.getlist("roles")
        access_scope = request.POST.get("access_scope")
        work_type_access = request.POST.getlist("work_type_access")

        if not user_id:
            messages.error(request, "Invalid user")
            return redirect("accounts_app:user_master")

        if not roles:
            messages.error(request, "At least one role is required")
            return redirect("accounts_app:user_master")

        if access_scope not in ACCESS_CHOICES:
            messages.error(request, "Invalid access scope")
            return redirect("accounts_app:user_master")

        users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "full_name": request.POST.get("full_name"),
                "mobile": request.POST.get("mobile"),
                "dob": request.POST.get("dob") or None,
                "department": request.POST.get("department"),
                "roles": roles,
                "access_scope": access_scope,
                "is_active": request.POST.get("is_active") == "true",
                "work_type_access": work_type_access,  # ✅ NEW
            }}
        )

        messages.success(request, "User updated successfully")
        return redirect("accounts_app:user_master")

    # ================= FETCH USERS =================
    users = list(users_col.find())

    for u in users:
        u["id"] = str(u["_id"])
        u["roles"] = u.get("roles", [])
        u["access_scope"] = u.get("access_scope", "OWN")
        u["work_type_access"] = u.get("work_type_access", [])

    return render(
        request,
        "accounts_app/user_master.html",
        {
            "users": users,
            "ROLE_CHOICES": ROLE_CHOICES,
            "ACCESS_CHOICES": ACCESS_CHOICES,
        }
    )


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


# Device Name
@mongo_login_required
def get_device_name(request):
    ua = request.META.get("HTTP_USER_AGENT", "").lower()
    if "windows" in ua:
        return "Windows Browser"
    if "android" in ua:
        return "Android Device"
    if "iphone" in ua:
        return "iPhone"
    if "mac" in ua:
        return "Mac Browser"
    return "Unknown Device"

# Record Login Info
def record_login(request, user):
    login_activity_col = get_login_activity_collection()

    device_id = request.session.get("device_id")
    if not device_id:
        return  # safety

    users_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {"active_device_id": device_id}}
    )

    activity_id = login_activity_col.insert_one({
        "user_id": str(user["_id"]),
        "username": user["username"],
        "device_id": device_id,
        "login_time": datetime.utcnow(),
        "logout_time": None
    }).inserted_id

    request.session["login_activity_id"] = str(activity_id)
# def record_login(request, user):
#     login_activity_col = get_login_activity_collection()
#
#     # 🔹 Unique device id per browser
#     device_id = request.session.get("device_id")
#     if not device_id:
#         device_id = str(uuid.uuid4())
#         request.session["device_id"] = device_id
#
#     login_time = datetime.utcnow()
#
#     activity_id = login_activity_col.insert_one({
#         "user_id": str(user["_id"]),
#         "username": user["username"],
#
#         "device_id": device_id,
#         "device_name": get_device_name(request),
#
#         "login_time": login_time,
#         "logout_time": None,
#         "session_duration": None,
#
#         "ip_address": request.META.get("REMOTE_ADDR"),
#         "user_agent": request.META.get("HTTP_USER_AGENT"),
#     }).inserted_id
#
#     request.session["login_time"] = login_time.isoformat()
#     request.session["login_activity_id"] = str(activity_id)


# Record Logout Info
@mongo_login_required
def record_logout(request):
    activity_id = request.session.get("login_activity_id")
    login_time_str = request.session.get("login_time")

    if not activity_id or not login_time_str:
        return

    login_activity_col = get_login_activity_collection()

    login_time = datetime.fromisoformat(login_time_str)
    logout_time = datetime.utcnow()

    login_activity_col.update_one(
        {"_id": ObjectId(activity_id)},
        {
            "$set": {
                "logout_time": logout_time,
                "session_duration": (logout_time - login_time).total_seconds()
            }
        }
    )