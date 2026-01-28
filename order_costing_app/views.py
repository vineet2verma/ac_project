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
    # order["id"] = str(order["_id"])
    if not order:
        return render(request, "404.html")

    order["id"] = str(order["_id"])
    order_id_str = str(order_oid)

    # ---------- MATERIAL COST ----------
    material_cost = sum(
        l.get("total_cost", 0)
        for l in ledger_col.find({
            "order_id": order_oid,
            "txn_type": "CONSUME"
        })
    )

    # ---------- MACHINE COST + Hours ----------
    machine_cost = 0
    machine_hours = 0
    machine_rows = []

    for m in machine_col.find({
        "order_id": order_id_str,
        "status": "COMPLETED"
    }):
        hours = float(m.get("working_hour", 0))
        machine_hours += hours

        mach = machine_master.find_one(
            {"_id": ObjectId(m["machine_id"])},
            {"machine_name": 1, "hourly_rate": 1}
        ) or {}

        rate = float(mach.get("hourly_rate", 0))
        cost = hours * rate
        machine_cost += cost

        machine_rows.append({
            "machine_name": m.get("machine_name", "-"),
            "hours": hours,
            "rate": rate,
            "cost": cost
        })

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
            float(dispatch.get("freight_cost", 0)) +
            float(dispatch.get("loading_cost", 0))
    )

    # ---------- TOTAL COST ----------
    total_cost = (
            material_cost +
            machine_cost +
            design_cost +
            qc_cost +
            dispatch_cost
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
        key = str(l.get("item_id"))
        # key = str(l["item_id"])

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
            "order_id": order["id"],
            # MATERIAL
            "material_rows": material_rows,
            "material_cost": material_cost,
            # MACHINE
            "machine_rows": machine_rows,
            "machine_hours": machine_hours,
            "machine_cost": machine_cost,
            # OTHER COSTS
            "design_cost": design_cost,
            "qc_cost": qc_cost,
            "dispatch_cost": dispatch_cost,
            # TOTAL
            "total_cost": total_cost,
        }
    )
