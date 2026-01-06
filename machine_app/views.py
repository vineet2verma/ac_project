from datetime import datetime, date
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect
from cnc_work_app.mongo import *
from bson import ObjectId
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404


# Create your views here.

# # Machine Master
# ================= MACHINE MASTER LIST =================
def machine_master_view(request):
    col = get_machine_master_collection()
    machines = list(col.find().sort("created_at", -1))
    # Mongo _id → string for template
    for m in machines: m["id"] = str(m["_id"])
    return render(request,"machine_app/machine_master_add.html",{"machines": machines})

@require_POST
def machine_master_add(request):
    col = get_machine_master_collection()
    machine_name = request.POST.get("machine_name", "").strip()
    machine_code = request.POST.get("machine_code", "").strip()
    is_active = request.POST.get("is_active") == "on"
    if not machine_name or not machine_code: return redirect("machine_app:machine_master_view")

    col.insert_one({
        "machine_name": machine_name,
        "machine_code": machine_code,
        "is_active": is_active,
        "created_at": timezone.now()
    })
    return redirect("machine_app:machine_master_view")

# ================= TOGGLE ACTIVE / INACTIVE IN MASTER=================
@require_POST
def machine_master_toggle(request, pk):
    col = get_machine_master_collection()
    try:
        oid = ObjectId(pk)
    except Exception:
        return redirect("machine_app:machine_master_view")

    machine = col.find_one({"_id": oid})
    if machine:
        col.update_one(
            {"_id": oid},
            {"$set": {"is_active": not machine.get("is_active", True)}}
        )

    return redirect("machine_app:machine_master_view")


# Add Machine For Order Work
def add_machine_work(request, order_id):
    if request.method == "POST":
        machine_id = request.POST.get("machine_id")
        work_type = request.POST.get("work_type", "ONTIME")
        working_hour = float(request.POST.get("working_hour"))
        operator = request.POST.get("operator")
        remarks = request.POST.get("remarks")

        master_col = get_machine_master_collection()
        machine = master_col.find_one({"_id": ObjectId(machine_id)})

        work_col = get_machine_work_collection()
        work_col.insert_one({
            "order_id": order_id,
            "machine_id": machine_id,
            "machine_name": machine["machine_name"],
            "work_type": work_type,
            "work_date": date.today().isoformat(),   # ✅ default today
            "working_hour": working_hour,
            "operator": operator,
            "remarks": remarks,
            "created_at": datetime.utcnow()
        })

    return redirect("cnc_work_app:detail", pk=order_id)

# Machine Delete From Order -----
def machine_delete(request, order_id, machine_work_id):
    if request.method == "POST":
        col = get_machine_work_collection()
        col.delete_one({"_id": ObjectId(machine_work_id)})
    return redirect("cnc_work_app:detail", pk=order_id)

# Machine Edit In Order -----
def machine_edit(request, order_id, machine_work_id):
    col = get_machine_work_collection()

    if request.method == "POST":
        col.update_one(
            {"_id": ObjectId(machine_work_id)},
            {"$set": {
                "machine_id": request.POST.get("machine_id"),   # ✅ optional but correct
                "working_hour": float(request.POST.get("working_hour", 0)),
                "work_type": request.POST.get("work_type", "ONTIME"),  # ✅ FIX
                "operator": request.POST.get("operator"),
                "remarks": request.POST.get("remarks"),
            }}
        )

    return redirect("cnc_work_app:detail", pk=order_id)
