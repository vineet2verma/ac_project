import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
from utils.mongo import todo_collection
from utils.common_func import mongo_login_required,mongo_role_required


@csrf_exempt
def api_todo_add(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    if not request.body:
        return JsonResponse({"error": "Empty body"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    todo_collection().insert_one({
        "task": data["task"],
        "task_date": data["task_date"],
        "done_requested": False,
        "done_approved": False,
        "created_by": data.get("created_by", "API"),
        "created_at": datetime.now(),
        "approved_by": None,
        "approved_at": None
    })

    return JsonResponse({"status": "success"}, status=201)


@mongo_login_required
def api_todo_list(request):
    col = todo_collection()
    todos = []

    # 📊 COUNTS (FAST & CORRECT)
    counts = {
        "total": col.count_documents({}),
        "pending": col.count_documents({"done_approved": False}),
        "completed": col.count_documents({"done_approved": True}),
    },

    for t in col.find().sort("created_at", -1):
        todos.append({
            "id": str(t.get("_id")),
            "task": t.get("task", ""),
            "task_date": t.get("task_date", ""),
            "done_requested": bool(t.get("done_requested", False)),
            "done_approved": bool(t.get("done_approved", False)),
            "created_by": t.get("created_by", ""),

            # ✅ SAFE datetime conversion
            "created_at": (
                t["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(t.get("created_at"), datetime)
                else None
            )
        })

    return JsonResponse({"count": counts, "data": todos,  }, status=200)


@csrf_exempt
def api_todo_update(request, todo_id):
    if request.method != "PUT":
        return JsonResponse({"error": "PUT required"}, status=405)

    data = json.loads(request.body.decode("utf-8"))

    todo_collection().update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": {
            "task": data["task"],
            "task_date": data["task_date"],
            "updated_at": datetime.now()
        }}
    )

    return JsonResponse({"status": "updated"})


@csrf_exempt
def api_todo_delete(request, todo_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "DELETE required"}, status=405)

    todo_collection().delete_one({"_id": ObjectId(todo_id)})
    return JsonResponse({"status": "deleted"})


@csrf_exempt
def api_request_done(request, todo_id):
    todo_collection().update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": {"done_requested": True}}
    )
    return JsonResponse({"status": "requested"})


@csrf_exempt
def api_approve_done(request, todo_id):
    data = json.loads(request.body.decode("utf-8"))

    todo_collection().update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": {
            "done_approved": True,
            "approved_by": data.get("approved_by"),
            "approved_at": datetime.now()
        }}
    )
    return JsonResponse({"status": "approved"})
