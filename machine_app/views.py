
from datetime import datetime, date
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from cnc_work_app.mongo import *
from bson import ObjectId

# Create your views here.
# # Machine Master
# ================= MACHINE MASTER LIST =================
def machine_master_view(request):
    col = get_machine_master_collection()
    machines = list(col.find().sort("created_at", -1))
    for m in machines:
        m["id"] = str(m["_id"])
    return render(request, "machine_app/machine_master_add.html", {
        "machines": machines
    })

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
        work_col = get_machine_work_collection()
        work_id = request.POST.get("machine_work_id")

        data = {
            "machine_id": request.POST["machine_id"],
            "work_type": request.POST.get("work_type", "ONTIME"),
            "working_hour": float(request.POST.get("working_hour", 0)),
            "operator": request.POST.get("operator"),
            "remarks": request.POST.get("remarks"),
        }

        # -------- EDIT (only if PENDING) --------
        if work_id:
            work = work_col.find_one({"_id": ObjectId(work_id)})
            if work and work["status"] == "PENDING":
                work_col.update_one(
                    {"_id": work["_id"]},
                    {"$set": data}
                )

        # -------- ADD --------
        else:
            machine = get_machine_master_collection().find_one(
                {"_id": ObjectId(request.POST["machine_id"])}
            )

            work_col.insert_one({
                "order_id": order_id,
                "machine_id": request.POST["machine_id"],
                "machine_name": machine["machine_name"],
                "work_type": data["work_type"],
                "work_date": date.today().isoformat(),
                "working_hour": data["working_hour"],
                "operator": data["operator"],
                "remarks": data["remarks"],
                "status": "PENDING",
                "created_at": datetime.now()
            })

    return redirect("cnc_work_app:detail", pk=order_id)


@require_POST
def machine_work_start(request, order_id, work_id):
    work_col = get_machine_work_collection()
    order_inv_col = get_order_inventory_collection()
    ledger_col = get_inventory_ledger_collection()
    design_col = get_design_files_collection()

    work = work_col.find_one({"_id": ObjectId(work_id)})
    if not work or work.get("status") != "PENDING":
        return redirect("cnc_work_app:detail", pk=order_id)

    # ===== CONSUME INVENTORY =====
    reserved_items = list(order_inv_col.find({
        "order_id": order_id,
        "status": "RESERVED"
    }))

    for r in reserved_items:
        order_inv_col.update_one(
            {"_id": r["_id"]},
            {"$set": {
                "status": "CONSUMED",
                "consumed_at": datetime.now()
            }}
        )

        ledger_col.insert_one({
            "item_id": r["inventory_id"],
            "item_name": r["item_name"],
            "order_id": order_id,
            "qty": r["reserved_qty"],
            "txn_type": "CONSUME",
            "source": "MACHINE_START",
            "ref_id": ObjectId(work_id),   # ✅ FIXED
            "created_at": datetime.now()
        })

    # ===== LOCK DESIGN =====
    design_col.update_many(
        {"order_id": order_id, "status": "APPROVED"},
        {"$set": {"status": "USED", "used_at": datetime.now()}}
    )

    # ===== START MACHINE =====
    work_col.update_one(
        {"_id": ObjectId(work_id)},
        {"$set": {
            "status": "IN_PROGRESS",
            "started_at": datetime.now()
        }}
    )

    return redirect("cnc_work_app:detail", pk=order_id)


@require_POST
def machine_work_complete(request, order_id, work_id):
    work_col = get_machine_work_collection()

    work_col.update_one(
        {"_id": ObjectId(work_id), "status": "IN_PROGRESS"},
        {"$set": {
            "status": "COMPLETED",
            "completed_at": datetime.now()
        }}
    )

    return redirect("cnc_work_app:detail", pk=order_id)


# Machine Delete Only if Pending From Order -----
@require_POST
def machine_delete(request, order_id, work_id):
    col = get_machine_work_collection()
    m = col.find_one({"_id": ObjectId(work_id)})
    if m and m["status"] == "PENDING":
        col.delete_one({"_id": m["_id"]})
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

