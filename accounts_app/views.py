import random
import string
import uuid
from bson import ObjectId
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from utils.mongo import users_collection,get_login_activity_collection
from utils.cookies import set_cookie, delete_cookie
from django.shortcuts import render, redirect
from utils.common_func import mongo_role_required, mongo_login_required

def get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0]
    return request.META.get("REMOTE_ADDR")


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
        # -------------------------
        # 1️⃣ GET FORM DATA
        # -------------------------
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "").strip()
        remember_me = request.POST.get("remember_me")

        # -------------------------
        # 2️⃣ AUTHENTICATE USER
        # -------------------------
        user = users_collection().find_one({
            "username": username,
            "is_active": True
        })

        if not user or not check_password(password, user.get("password")):
            messages.error(request, "Invalid username or password")
            return render(request, "accounts_app/login.html")

        # -------------------------
        # 3️⃣ SET SESSION
        # -------------------------
        request.session.flush()  # clear old session safely

        request.session["mongo_user_id"] = str(user["_id"])
        request.session["mongo_username"] = user["username"]
        request.session["mongo_roles"] = user.get("roles", [])
        request.session["access_scope"] = user.get("access_scope", "OWN")
        request.session["work_type_access"] = user.get("work_type_access", [])

        # Session expiry
        request.session.set_expiry(
            60 * 60 * 24 * 7 if remember_me else 0
        )

        # -------------------------
        # 4️⃣ DEVICE / BROWSER INFO
        # -------------------------
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        ua = user_agent.lower()

        # Device
        if "mobile" in ua:
            device = "Mobile"
        elif "tablet" in ua or "ipad" in ua:
            device = "Tablet"
        else:
            device = "Desktop"

        # Browser
        if "edg" in ua:
            browser = "Edge"
        elif "chrome" in ua:
            browser = "Chrome"
        elif "firefox" in ua:
            browser = "Firefox"
        elif "safari" in ua:
            browser = "Safari"
        else:
            browser = "Other"

        # OS
        if "windows" in ua:
            os_name = "Windows"
        elif "android" in ua:
            os_name = "Android"
        elif "iphone" in ua or "ipad" in ua:
            os_name = "iOS"
        elif "linux" in ua:
            os_name = "Linux"
        else:
            os_name = "Other"

        ip_address = get_client_ip(request)

        # -------------------------
        # 5️⃣ LOGIN ACTIVITY LOG
        # -------------------------
        device_id = str(uuid.uuid4())
        request.session["device_id"] = device_id

        result = get_login_activity_collection().insert_one({
            "user_id": user["_id"],
            "username": user["username"],
            "login_time": timezone.now(),
            "logout_time": None,
            "device_id": device_id,
            "device": device,
            "browser": browser,
            "os": os_name,
            "ip_address": ip_address,
        })

        # save activity id for logout
        request.session["login_activity_id"] = str(result.inserted_id)

        # -------------------------
        # 6️⃣ REDIRECT (NO LOOP)
        # -------------------------
        roles = user.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]

        response = redirect(
            "core_app:dashboard"
            if "ADMIN" in roles
            else "cnc_work_app:index"
        )

        # Remember-me cookie (optional)
        if remember_me:
            set_cookie(response, "remember_token", str(user["_id"]), days=7)

        return response

    # -------------------------
    # GET REQUEST
    # -------------------------
    return render(request, "accounts_app/login.html")


@mongo_login_required
def logout_view(request):
    response = redirect("accounts_app:login")
    delete_cookie(response, "username")
    delete_cookie(response, "primary_role")
    record_logout(request)  # 🔥 save logout activity

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


# Record Logout Info
@mongo_login_required
def record_logout(request):
    activity_id = request.session.get("login_activity_id")

    if not activity_id:
        return

    logout_time = timezone.now()

    get_login_activity_collection().update_one(
        {"_id": ObjectId(activity_id), "logout_time": None},
        {
            "$set": {
                "logout_time": logout_time
            }
        }
    )