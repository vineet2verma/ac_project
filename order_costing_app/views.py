from datetime import datetime
from django.shortcuts import render, redirect
from utils.mongo import *
from bson import ObjectId
from collections import defaultdict
from accounts_app.views import mongo_login_required, mongo_role_required

# Create your views here.

@mongo_login_required
def rate_config_view(request):
    rate_col = get_rate_config_collection()

    # Fetch existing config (single doc)
    config = rate_col.find_one() or {}

    if request.method == "POST":

        data = {
            "material": {
                "calculation": request.POST.get("material_calculation"),
                "default_unit_rate": float(request.POST.get("material_rate", 0))
            },
            "machine": {
                "default_hourly_rate": float(request.POST.get("machine_rate", 0)),
                "use_master": bool(request.POST.get("machine_use_master"))
            },
            "design": {
                "default_rate_per_hour": float(request.POST.get("design_rate", 0))
            },
            "qc": {
                "calculation": request.POST.get("qc_calculation"),
                "rate_per_order": float(request.POST.get("qc_rate_order", 0)),
                "rate_per_item": float(request.POST.get("qc_rate_item", 0))
            },
            "dispatch": {
                "freight_default": float(request.POST.get("freight_rate", 0)),
                "loading_default": float(request.POST.get("loading_rate", 0))
            },
            "updated_at": datetime.now()
        }

        if config:
            rate_col.update_one({}, {"$set": data})
        else:
            rate_col.insert_one(data)

        return redirect("cnc_work_app:index")

    return render(
        request,
        "rate_config/rate_config.html",
        {"config": config}
    )

@mongo_login_required
def order_costing_view(request, order_id):

    # ---------- COLLECTIONS ----------
    order_col = get_orders_collection()
    ledger_col = get_inventory_ledger_collection()
    machine_col = get_machine_work_collection()
    machine_master = get_machine_master_collection()
    design_col = get_design_files_collection()
    qc_col = get_quality_collection()
    dispatch_col = get_dispatch_collection()
    rate_col = get_rate_config_collection()

    # ---------- DEFAULT RATE CONFIG (MANDATORY) ----------
    DEFAULT_RATE_CONFIG = {
        "material": {
            "calculation": "ledger",
            "default_unit_rate": 0
        },
        "machine": {
            "default_hourly_rate": 0,
            "use_master": True
        },
        "design": {
            "default_rate_per_hour": 0
        },
        "qc": {
            "calculation": "flat",
            "rate_per_order": 0,
            "rate_per_item": 0
        },
        "dispatch": {
            "freight_default": 0,
            "loading_default": 0
        }
    }

    db_config = rate_col.find_one() or {}

    # ---------- MERGE CONFIG SAFELY ----------
    RATE_CONFIG = DEFAULT_RATE_CONFIG
    for key in DEFAULT_RATE_CONFIG:
        RATE_CONFIG[key].update(db_config.get(key, {}))

    # ---------- ORDER ----------
    order_oid = ObjectId(order_id)
    order = order_col.find_one({"_id": order_oid})

    if not order:
        return render(request, "404.html")

    order["id"] = str(order["_id"])
    order_id_str = str(order_oid)

    # =========================================================
    # MATERIAL COST
    # =========================================================
    material_cost = 0
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
        qty = float(l.get("qty", 0))
        unit_cost = float(
            l.get("unit_cost", RATE_CONFIG["material"]["default_unit_rate"])
        )
        total = qty * unit_cost
        material_cost += total

        key = str(l.get("item_id"))
        material_map[key]["item_name"] = l.get("item_name", "-")
        material_map[key]["qty"] += qty
        material_map[key]["unit_cost"] = unit_cost
        material_map[key]["total_cost"] += total

    material_rows = list(material_map.values())

    # =========================================================
    # MACHINE COST
    # =========================================================
    machine_cost = 0
    machine_hours = 0
    machine_rows = []

    for m in machine_col.find({
        "order_id": order_id_str,
        "status": "COMPLETED"
    }):
        hours = float(m.get("working_hour", 0))
        machine_hours += hours

        rate = RATE_CONFIG["machine"]["default_hourly_rate"]
        mach = {}

        if RATE_CONFIG["machine"]["use_master"]:
            mach = machine_master.find_one(
                {"_id": ObjectId(m.get("machine_id"))},
                {"machine_name": 1, "hourly_rate": 1}
            ) or {}
            rate = float(mach.get("hourly_rate", rate))

        cost = hours * rate
        machine_cost += cost

        machine_rows.append({
            "machine_name": mach.get("machine_name", "-"),
            "hours": hours,
            "rate": rate,
            "cost": cost
        })

    # =========================================================
    # DESIGN COST
    # =========================================================
    design_cost = 0

    for d in design_col.find({
        "order_id": order_oid,
        "status": {"$in": ["APPROVED", "USED"]}
    }):
        hours = float(d.get("hours", 0))
        rate = float(
            d.get("rate_per_hour", RATE_CONFIG["design"]["default_rate_per_hour"])
        )
        design_cost += hours * rate

    # =========================================================
    # QC COST
    # =========================================================
    if RATE_CONFIG["qc"]["calculation"] == "flat":
        qc_cost = RATE_CONFIG["qc"]["rate_per_order"]
    else:
        qc_count = qc_col.count_documents({
            "order_id": order_oid,
            "status": "PASSED"
        })
        qc_cost = qc_count * RATE_CONFIG["qc"]["rate_per_item"]

    # =========================================================
    # DISPATCH COST
    # =========================================================
    dispatch = dispatch_col.find_one({
        "order_id": order_oid,
        "status": "DISPATCHED"
    }) or {}

    dispatch_cost = (
        float(dispatch.get("freight_cost", RATE_CONFIG["dispatch"]["freight_default"])) +
        float(dispatch.get("loading_cost", RATE_CONFIG["dispatch"]["loading_default"]))
    )

    # =========================================================
    # TOTAL COST
    # =========================================================
    total_cost = round(
        material_cost +
        machine_cost +
        design_cost +
        qc_cost +
        dispatch_cost, 2
    )

    # ---------- RENDER ----------
    return render(
        request,
        "order_costing/order_costing.html",
        {
            "order": order,
            "order_id": order["id"],
            "material_rows": material_rows,
            "material_cost": material_cost,
            "machine_rows": machine_rows,
            "machine_hours": machine_hours,
            "machine_cost": machine_cost,
            "design_cost": design_cost,
            "qc_cost": qc_cost,
            "dispatch_cost": dispatch_cost,
            "total_cost": total_cost,
            "rate_config": RATE_CONFIG,
        }
    )


