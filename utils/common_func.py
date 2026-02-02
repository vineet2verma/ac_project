import uuid
from functools import wraps
from django.http import JsonResponse

from .mongo import *
from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password

def get_active_sales_users():
    return list(
        users_collection().find(
            {"roles": "SALES", "is_active": True},
            {"_id": 0, "username": 1, "full_name": 1, "email": 1, "roles": 1}
        ).sort("username", 1)
    )


def mongo_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("mongo_user_id"):
            return redirect("accounts_app:login")
        return view_func(request, *args, **kwargs)

    return wrapper

# def mongo_login_required(view_func):
#     def wrapper(request, *args, **kwargs):
#         user_id = request.session.get("mongo_user_id")
#         device_id = request.session.get("device_id")
#         if not user_id:
#             return redirect("accounts_app:login")
#         user = users_collection().find_one({"_id": ObjectId(user_id)})
#         if not user :
#             request.session.flush()
#             return redirect("accounts_app:login")
#
#         # 🔥 DEVICE CHECK (FIXED)
#         active_device_id = user.get("active_device_id")
#
#         if active_device_id and device_id and active_device_id != device_id:
#
#             request.session.flush()
#             messages.error(
#                 request,
#                 "You were logged out because your account was logged in from another device."
#             )
#             return redirect("accounts_app:login")
#
#         return view_func(request, *args, **kwargs)
#
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


@csrf_exempt
def mongo_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    username = request.POST.get("username", "").strip().lower()
    password = request.POST.get("password", "").strip()

    user = users_collection().find_one({
        "username": username,
        "is_active": True
    })

    if not user or not check_password(password, user["password"]):
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    device_id = str(uuid.uuid4())

    request.session["mongo_user_id"] = str(user["_id"])
    request.session["device_id"] = device_id
    request.session["mongo_roles"] = user.get("roles", [])

    users_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {"active_device_id": device_id}}
    )

    return JsonResponse({
        "status": "success",
        "user_id": str(user["_id"]),
        "roles": user.get("roles", [])
    })