from datetime import datetime, date
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from cnc_work_app.mongo import *
from bson import ObjectId
from collections import defaultdict


# Create your views here.
def order_costing_view(request, order_id):

    # ---------- COLLECTIONS ----------
    order_col = get_orders_collection()
    ledger_col = get_inventory_ledger_collection()
    machine_col = get_machine_work_collection()
    machine_master = get_machine_master_collection()
    design_col = get_design_files_collection()
    qc_col = get_quality_collection()
    dispatch_col = get_dispatch_collection()

    # ---------- ORDER ----------
    order_oid = ObjectId(order_id)
    order = order_col.find_one({"_id": ObjectId(order_id)})
    order["id"] = str(order["_id"])

    # ---------- MATERIAL COST ----------
    material_cost = sum(
        l.get("total_cost", 0)
        for l in ledger_col.find({
            "order_id": order_oid,
            "txn_type": "CONSUME"
        })
    )

    # ---------- MACHINE COST ----------
    machine_cost = 0
    for m in machine_col.find({
        "order_id": order_oid,
        "status": "COMPLETED"
    }):
        mach = machine_master.find_one(
            {"machine_name": m["machine_name"]},
            {"hourly_rate": 1}
        )
        if mach:
            machine_cost += m.get("working_hour", 0) * mach.get("hourly_rate", 0)

    # ---------- DESIGN COST ----------
    design_cost = sum(
        d.get("hours", 0) * d.get("rate_per_hour", 0)
        for d in design_col.find({
            "order_id": order_oid,
            "status": {"$in": ["APPROVED", "USED"]}
        })
    )

    # ---------- QC COST ----------
    qc_cost = sum(
        q.get("qc_cost", 0)
        for q in qc_col.find({
            "order_id": order_oid,
            "status": "PASSED"
        })
    )

    # ---------- DISPATCH COST ----------
    dispatch = dispatch_col.find_one({
        "order_id": order_oid,
        "status": "DISPATCHED"
    }) or {}

    dispatch_cost = (
        dispatch.get("freight_cost", 0)
        + dispatch.get("loading_cost", 0)
    )

    total_cost = (
        material_cost
        + machine_cost
        + design_cost
        + qc_cost
        + dispatch_cost
    )

    # ---------- MATERIAL BREAKDOWN ----------
    material_rows = []
    material_map = defaultdict(lambda: {
        "item_name": "",
        "qty": 0,
        "unit_cost": 0,
        "total_cost": 0
    })

    for l in ledger_col.find({
        "order_id": order_oid,
        "txn_type": "CONSUME"
    }):
        key = str(l["item_id"])

        material_map[key]["item_name"] = l.get("item_name", "-")
        material_map[key]["qty"] += float(l.get("qty", 0))
        material_map[key]["unit_cost"] = float(l.get("unit_cost", 0))
        material_map[key]["total_cost"] += float(l.get("total_cost", 0))

    material_rows = list(material_map.values())

    return render(
        request,
        "order_costing/order_costing.html",
        {
            "order": order,
            "order_id": str(order["id"]),
            "material_rows": material_rows,  # ✅ NEW
            "material_cost": material_cost,
            "machine_cost": machine_cost,
            "design_cost": design_cost,
            "qc_cost": qc_cost,
            "dispatch_cost": dispatch_cost,
            "total_cost": total_cost,
        }
    )