from datetime import datetime, date
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, Http404
from django.core.paginator import Paginator
from bson import ObjectId
from cnc_work_app.mongo import todo_collection


def todo_list(request):
    col = todo_collection()
    username = request.session.get("mongo_username")
    roles = request.session.get("mongo_roles", [])
    q = request.GET.get("q", "")
    status = request.GET.get("status", "pending")
    limit = int(request.GET.get("limit", 10))
    page_number = request.GET.get("page", 1)

    query = {}

    if "ADMIN" not in roles:
        query["created_by"] = username

    if q:
        query["task"] = {"$regex": q, "$options": "i"}

    if status == "pending":
        query["done_approved"] = False
    elif status == "completed":
        query["done_approved"] = True

    todos = list(col.find(query).sort("created_at", -1))

    for t in todos:
        t["id"] = str(t["_id"])
        t["task_date_obj"] = (
            datetime.strptime(t["task_date"], "%Y-%m-%d").date()
            if isinstance(t.get("task_date"), str)
            else t["task_date"]
        )

        t["is_overdue"] = (
            not t.get("done_approved", False)
            and t["task_date_obj"] < date.today()
        )

        t["needs_approval"] = (
            t.get("done_requested", False)
            and not t.get("done_approved", False)
        )

    paginator = Paginator(todos, limit)
    page_obj = paginator.get_page(page_number)

    return render(request, "todo_app/todo_list.html", {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "limit": limit,
        "limits": [10, 25, 50, 100],
        "today": date.today(),
        "roles": roles
    })


def todo_add(request):
    if request.method == "POST":
        todo_collection().insert_one({
            "task": request.POST.get("task"),
            "task_date": request.POST.get("task_date"),
            "done_requested": False,
            "done_approved": False,
            "created_by": request.session["mongo_username"],
            "created_at": datetime.now(),
            "approved_by": None,
            "approved_at": None
        })
    return redirect("todo_app:list")


def request_done(request, todo_id):
    todo_collection().update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": {"done_requested": True}}
    )
    return redirect("todo_app:list")


def approve_done(request, todo_id):
    todo_collection().update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": {
            "done_approved": True,
            "approved_by": request.session["mongo_username"],
            "approved_at": datetime.now()
        }}
    )
    return redirect("todo_app:list")


def todo_edit(request, todo_id):
    col = todo_collection()
    todo = col.find_one({"_id": ObjectId(todo_id)})
    if not todo:
        raise Http404("Todo not found")

    todo["id"] = str(todo["_id"])

    if request.method == "POST":
        col.update_one(
            {"_id": ObjectId(todo_id)},
            {"$set": {
                "task": request.POST.get("task"),
                "task_date": request.POST.get("task_date"),
                "updated_at": datetime.now()
            }}
        )
        return redirect("todo_app:list")

    return render(request, "todo_app/todo_edit.html", {"todo": todo})


def todo_delete(request, todo_id):
    todo_collection().delete_one({"_id": ObjectId(todo_id)})
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/todo/"))


def todo_dashboard(request):
    col = todo_collection()
    username = request.session["mongo_username"]

    stats = {
        "total": col.count_documents({"created_by": username}),
        "pending": col.count_documents({"created_by": username, "done_approved": False}),
        "completed": col.count_documents({"created_by": username, "done_approved": True}),
        "waiting_approval": col.count_documents({
            "created_by": username,
            "done_requested": True,
            "done_approved": False
        })
    }

    return render(request, "todo_app/dashboard.html", {"stats": stats})
