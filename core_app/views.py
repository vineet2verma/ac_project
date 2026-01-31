import pandas as pd
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from accounts_app.views import mongo_login_required, mongo_role_required
from cnc_work_app.mongo import *
from datetime import datetime, timedelta

from reportlab.platypus import SimpleDocTemplate, Table


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
        # 1️⃣ Break order_status array
        {"$unwind": "$order_status"},

        # 2️⃣ Only pending statuses
        {
            "$match": {
                "order_status.status": "PENDING"
            }
        },

        # 3️⃣ Group by stage
        {
            "$group": {
                "_id": "$order_status.stage",
                "count": {"$sum": 1}
            }
        }
    ]

    result = order_col.aggregate(pipeline)

    # 🔹 STAGE → KEY MAPPING
    stage_map = {
        "DESIGN": "design",
        "INVENTORY": "inventory",
        "MACHINE": "machine",
        "QC": "qc",
        "DISPATCH": "dispatch",
    }

    # Default response (zero-safe)
    counts = {
        "design": 0,
        "inventory": 0,
        "machine": 0,
        "qc": 0,
        "dispatch": 0,
    }

    for r in result:
        key = stage_map.get(r["_id"])
        if key:
            counts[key] = r["count"]

    return counts


# Sales Person Report
def get_sales_person_order_counts():
    order_col = get_orders_collection()
    users_col = users_collection()

    pipeline = [
        # 1️⃣ Only active SALES users
        {
            "$match": {
                "roles": "SALES",
                "is_active": True
            }
        },

        # 2️⃣ Lookup orders by username
        {
            "$lookup": {
                "from": order_col.name,
                "localField": "username",
                "foreignField": "sales_person",
                "as": "orders"
            }
        },

        # 3️⃣ Unwind orders (keep zero-order users)
        {
            "$unwind": {
                "path": "$orders",
                "preserveNullAndEmptyArrays": True
            }
        },

        # 4️⃣ Group by FULL NAME + USERNAME + STATUS
        {
            "$group": {
                "_id": {
                    "full_name": "$full_name",
                    "username": "$username",
                    "status": {
                        "$cond": [
                            {"$eq": ["$orders.current_status", "Complete"]},
                            "complete",
                            "pending"
                        ]
                    }
                },
                "count": {
                    "$sum": {
                        "$cond": [
                            {"$ifNull": ["$orders", False]},
                            1,
                            0
                        ]
                    }
                }
            }
        },

        # 5️⃣ Sort A → Z
        {
            "$sort": {
                "_id.full_name": 1
            }
        }
    ]

    result = users_col.aggregate(pipeline)

    sales_stats = {}

    for r in result:
        full_name = r["_id"]["full_name"]
        username = r["_id"]["username"]
        status = r["_id"]["status"]
        count = r["count"]

        if full_name not in sales_stats:
            sales_stats[full_name] = {
                "pending": 0,
                "complete": 0,
                "total": 0,
                "completion_pct": 0,
                "username": username
            }

        sales_stats[full_name][status] = count

    # 6️⃣ Calculate TOTAL & COMPLETION %
    for full_name, stats in sales_stats.items():
        pending = stats["pending"]
        complete = stats["complete"]
        total = pending + complete

        stats["total"] = total
        stats["completion_pct"] = (
            round((complete / total) * 100) if total > 0 else 0
        )

    return sales_stats


def sales_person_detail(request, username):
    order_col = get_orders_collection()
    users_col = users_collection()

    user = users_col.find_one({"username": username})
    full_name = user.get("full_name") if user else username

    orders = list(order_col.find({"sales_person": username}))

    pending = sum(1 for o in orders if o.get("current_status") != "Complete")
    complete = sum(1 for o in orders if o.get("current_status") == "Complete")

    # ✅ Normalize order data for template
    order_list = []

    for o in orders:
        # Check if any stage pending
        is_pending = any(
            s.get("status") == "PENDING" for s in o.get("order_status", [])
        )

        order_list.append({
            "order_no": o.get("title", "-"),
            "client_name": o.get("party_name", "-"),
            "image": o.get("image"),
            "status": "Pending" if is_pending else "Completed",
            "stages": o.get("order_status", []),  # 👈 stage wise
            "date": o.get("created_at")
        })

    context = {
        "sales_person": full_name,
        "username": username,
        "pending_count": pending,
        "complete_count": complete,
        "total_count": pending + complete,
        "orders": order_list
    }

    return render(request, "core_app/sales_person_detail.html", context)


def export_orders_pdf(request, username):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="orders.pdf"'

    doc = SimpleDocTemplate(response)
    data = [["Order", "Client", "Status"]]

    for o in get_orders_collection().find({"sales_person": username}):
        data.append([o["title"], o["party_name"], o["current_status"]])

    doc.build([Table(data)])
    return response


def export_orders_excel(request, username):
    order_col = get_orders_collection()
    users_col = users_collection()

    # Get sales person full name (for file name)
    user = users_col.find_one({"username": username})
    sales_person = user.get("full_name") if user else username

    # Fetch orders
    orders = list(order_col.find({"sales_person": username}))

    data = []

    for o in orders:
        # Determine overall order status from stages
        stages = o.get("order_status", [])
        is_pending = any(s.get("status") == "PENDING" for s in stages)

        data.append({
            "Order Title": o.get("title", "-"),
            "Client Name": o.get("party_name", "-"),
            "Stone": o.get("stone", "-"),
            "Color": o.get("color", "-"),
            "Type Of Work": o.get("type_of_work", "-"),
            "Status": "Pending" if is_pending else "Completed",
            "Created Date": o.get("created_at").strftime("%d-%m-%Y")
            if o.get("created_at") else "-"
        })

    # Create DataFrame
    df = pd.DataFrame(data)

    # Excel response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{sales_person}_orders.xlsx"'
    )

    # Write Excel
    df.to_excel(response, index=False)

    return response


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
                    "$addToSet": "$order.title"  # ✅ MULTIPLE ORDERS
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
        "inv_5day_summary": get_last_5_days_inventory_in_out_summary(),
        #
        # "order_lifecycle": get_pending_order_lifecycle_summary()
    }
    return render(request, "core_app/dashboard.html", context)


def error_page(request):
    return render(request, "404.html")


def custom_404_view(request, exception):
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(
            {"error": "Page not found"},
            status=404
        )
    return redirect("core_app:error_page")
