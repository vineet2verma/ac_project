from django.shortcuts import render
from accounts_app.views import mongo_login_required, mongo_role_required
from cnc_work_app.mongo import *
from datetime import datetime, timedelta

# Order Status Count
def get_order_counts():
    order_col = get_orders_collection()
    total_orders = order_col.count_documents({})
    complete_orders = order_col.count_documents({
        "current_status": "Complete"
    })
    pending_orders = order_col.count_documents({
        "current_status": {"$ne": "Complete"}
    })
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "complete_orders": complete_orders,
    }

# Inventory Reorder
def get_reorder_inventory_count():
    inv_col = get_inventory_master_collection()
    reorder_count = inv_col.count_documents({
        "$expr": {
            "$lt": ["$current_qty", "$reorder_level"]
        },
        "is_active": True
    })
    return reorder_count

# Order Status Count
def get_order_status_counts():
    order_col = get_orders_collection()
    pipeline = [
        {
            "$match": {
                "current_status": {
                    "$in": ["Design Pending", "Machine", "Inventory Pending", "QC", "Dispatch"]
                }
            }
        },
        {
            "$group": {
                "_id": "$current_status",
                "count": {"$sum": 1}
            }
        }
    ]

    result = order_col.aggregate(pipeline)

    # 🔹 STATUS → KEY MAPPING
    status_map = {
        "Design Pending": "design",
        "Machine": "machine",
        "Inventory Pending": "inventory",
        "QC": "qc",
        "Dispatch": "dispatch",
    }

    counts = {
        "design": 0,
        "machine": 0,
        "inventory": 0,
        "qc": 0,
        "dispatch": 0,
    }

    for r in result:
        key = status_map.get(r["_id"])
        if key:
            counts[key] = r["count"]

    return counts

# Sales Person Report
def get_sales_person_order_counts():
    order_col = get_orders_collection()
    users_col = users_collection()  # your users collection

    pipeline = [
        # 1️⃣ Join with users collection
        {
            "$lookup": {
                "from": users_col.name,   # IMPORTANT
                "localField": "sales_person",
                "foreignField": "username",
                "as": "user"
            }
        },

        # 2️⃣ Unwind joined user
        {"$unwind": "$user"},

        # 3️⃣ Filter only SALES role users
        {
            "$match": {
                "user.roles": "SALES",
                "user.is_active": True
            }
        },

        # 4️⃣ Group by sales person + status
        {
            "$group": {
                "_id": {
                    "sales_person": "$sales_person",
                    "status": {
                        "$cond": [
                            {"$eq": ["$current_status", "Complete"]},
                            "complete",
                            "pending"
                        ]
                    }
                },
                "count": {"$sum": 1}
            }
        }
    ]

    result = order_col.aggregate(pipeline)

    sales_stats = {}
    for r in result:
        person = r["_id"]["sales_person"]
        status = r["_id"]["status"]

        if person not in sales_stats:
            sales_stats[person] = {"pending": 0, "complete": 0}

        sales_stats[person][status] = r["count"]

    return sales_stats

# Machine Report
def get_last_5_days_machine_summary():
    report_col = get_machine_work_collection()
    order_col = get_orders_collection()

    start_date = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")

    pipeline = [
        {
            "$match": {
                "work_date": {"$gte": start_date}
            }
        },
        {
            "$addFields": {
                "order_obj_id": {
                    "$cond": [
                        {"$eq": [{"$type": "$order_id"}, "string"]},
                        {"$toObjectId": "$order_id"},
                        "$order_id"
                    ]
                }
            }
        },
        {
            "$lookup": {
                "from": order_col.name,
                "localField": "order_obj_id",
                "foreignField": "_id",
                "as": "order"
            }
        },
        {
            "$unwind": {
                "path": "$order",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$group": {
                "_id": {
                    "date": "$work_date",
                    "machine_name": "$machine_name"
                },
                "orders": {
                    "$addToSet": "$order.title"   # ✅ MULTIPLE ORDERS
                },
                "ontime": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$work_type", "ONTIME"]},
                            "$working_hour",
                            0
                        ]
                    }
                },
                "downtime": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$work_type", "DOWNTIME"]},
                            "$working_hour",
                            0
                        ]
                    }
                }
            }
        },
        {
            "$sort": {"_id.date": -1}
        }
    ]

    result = list(report_col.aggregate(pipeline))

    return [
        {
            "date": r["_id"]["date"],
            "machine_name": r["_id"]["machine_name"],
            "orders": [o for o in r["orders"] if o],  # remove None
            "ontime": r["ontime"],
            "downtime": r["downtime"],
        }
        for r in result
    ]

# 5 Days Inventory Summary - Ledger
def get_last_5_days_inventory_in_out_summary():
    col = get_inventory_ledger_collection()

    start_date = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")

    pipeline = [
        {
            "$match": {
                "created_at": {
                    "$gte": datetime.strptime(start_date, "%Y-%m-%d")
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "txn_type": "$txn_type"
                },
                "total_qty": {"$sum": "$qty"},
                "total_amount": {"$sum": "$amount"}
            }
        },
        {
            "$group": {
                "_id": "$_id.date",
                "in_qty": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$_id.txn_type", "IN"]},
                            "$total_qty",
                            0
                        ]
                    }
                },
                "in_amount": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$_id.txn_type", "IN"]},
                            "$total_amount",
                            0
                        ]
                    }
                },
                "out_qty": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$_id.txn_type", "OUT"]},
                            "$total_qty",
                            0
                        ]
                    }
                },
                "out_amount": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$_id.txn_type", "OUT"]},
                            "$total_amount",
                            0
                        ]
                    }
                }
            }
        },
        {
            "$sort": {"_id": -1}
        }
    ]

    result = list(col.aggregate(pipeline))

    return [
        {
            "date": r["_id"],
            "in_qty": r["in_qty"],
            "in_amount": r["in_amount"],
            "out_qty": r["out_qty"],
            "out_amount": r["out_amount"],
            "net_amount": r["in_amount"] - r["out_amount"]
        }
        for r in result
    ]

# Order Life Cycle Summary
def get_pending_order_lifecycle_summary():
    order_col = get_orders_collection()
    machine_col = get_machine_work_collection()
    ledger_col = get_inventory_ledger_collection()

    orders = list(order_col.find({
        "current_status": {"$ne": "Complete"}
    }).sort("created_at", -1))

    report = []

    for o in orders:
        order_id = o["_id"]

        # 🔹 DESIGN DAYS
        design_days = None
        if o.get("approval_date") and o.get("created_at"):
            design_days = (o["approval_date"] - o["created_at"]).days

        # 🔹 MACHINE HOURS + COST
        machine_data = list(machine_col.aggregate([
            {"$match": {"order_id": str(order_id)}},
            {
                "$group": {
                    "_id": None,
                    "hours": {"$sum": "$working_hour"}
                }
            }
        ]))
        machine_hours = machine_data[0]["hours"] if machine_data else 0
        machine_cost = machine_hours * o.get("machine_rate", 0)

        # 🔹 INVENTORY COST
        inv_data = list(ledger_col.aggregate([
            {
                "$match": {
                    "ref_id": str(order_id),
                    "txn_type": "OUT",
                    "source": "ORDER"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "items": {"$sum": 1},
                    "amount": {"$sum": "$amount"}
                }
            }
        ]))
        inv_items = inv_data[0]["items"] if inv_data else 0
        inv_cost = inv_data[0]["amount"] if inv_data else 0

        report.append({
            "order_id": str(order_id),
            "title": o.get("title"),
            "party": o.get("party_name"),
            "status": o.get("current_status"),
            "sales_person": o.get("sales_person"),

            "design_days": design_days,
            "machine_hours": machine_hours,
            "machine_cost": machine_cost,

            "inventory_items": inv_items,
            "inventory_cost": inv_cost,

            "qc_date": o.get("qc_date"),
            "dispatch_date": o.get("dispatch_date"),
        })

    return report

@mongo_login_required
@mongo_role_required(["ADMIN", "MANAGER"])
def dashboard(request):
    context = {
        # Order Count
        "order_status": get_order_counts(),
        # Reorder Count
        "reorder_count": get_reorder_inventory_count(),
        # Order Stage
        "order_stage_status": get_order_status_counts(),
        # Sales Person Reports
        "sales_person_stats": get_sales_person_order_counts(),
        # Machine Count
        "machine_reports": get_last_5_days_machine_summary(),
        # 5 days ledger in / out
        # "inv_5day_summary": get_last_5_days_inventory_in_out_summary(),
        #
        # "order_lifecycle": get_pending_order_lifecycle_summary()
    }
    return render(request, "core_app/dashboard.html", context)


