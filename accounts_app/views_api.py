from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from utils.mongo import users_collection
import uuid



def api_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    username = request.POST.get("username", "").strip().lower()
    password = request.POST.get("password", "").strip()

    col = users_collection()
    user = col.find_one({
        "username": username,
        "is_active": True
    })

    if not user:
        return JsonResponse({"error": "User not found"}, status=401)

    # ✅ PLAIN TEXT PASSWORD CHECK (your DB)
    if password != user.get("password"):
        return JsonResponse({"error": "Password mismatch"}, status=401)

    # 🔐 SESSION
    request.session["mongo_user_id"] = str(user["_id"])
    request.session["mongo_username"] = user["username"]
    request.session["mongo_roles"] = user.get("roles", [])

    # 🔑 DEVICE ID
    device_id = str(uuid.uuid4())
    request.session["device_id"] = device_id

    col.update_one(
        {"_id": user["_id"]},
        {"$set": {"active_device_id": device_id}}
    )

    return JsonResponse({
        "status": "success",
        "username": user["username"],
        "roles": user.get("roles", [])
    })