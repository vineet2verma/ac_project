from datetime import datetime, date
from bson import ObjectId
import openpyxl
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from cnc_work_app.mongo import (
    get_inventory_master_collection,
    get_inventory_ledger_collection,
    category_collection,
)
from django.http import Http404



# Inventory Master
def inventory_master_view(request):
    inv_col = get_inventory_master_collection()
    cat_col = category_collection()

    # ADD / UPDATE
    if request.method == "POST":
        item_id = request.POST.get("item_id")

        data = {
            "item_name": request.POST.get("item_name"),
            "category": request.POST.get("category"),
            "location": request.POST.get("location"),
            "unit": request.POST.get("unit"),
            "current_qty": float(request.POST.get("opening_qty", 0)),
            "rate": float(request.POST.get("rate")),
            "reorder_level": float(request.POST.get("reorder_level")),
            "is_active": True,
            "created_at": datetime.now()
        }

        if item_id:  # UPDATE
            inv_col.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": data}
            )
        else:  # ADD
            opening_qty = float(request.POST.get("opening_qty"))

            data.update({
                "opening_qty": opening_qty,
                "current_qty": opening_qty,
                "created_at": datetime.now()
            })
            inv_col.insert_one(data)

        return redirect("inv_app:inventory_master")

    # Inventory List
    items = list(inv_col.find({"is_active": True}).sort("created_at", -1))
    for i in items: i["id"] = str(i["_id"])

    # 🔹 CATEGORY LIST (for dropdown)
    categories = list(cat_col.find({"is_active": True}))
    for c in categories: c["id"] = str(c["_id"])

    return render(request, "inv_app/inventory_master.html", {
        "items": items,
        "categories": categories,
    })

def inventory_bulk_upload(request):
    if request.method == "POST":
        excel_file = request.FILES.get("excel_file")

        if not excel_file:
            return redirect("inv_app:inventory_master")

        wb = openpyxl.load_workbook(excel_file)
        sheet = wb.active

        inv_col = get_inventory_master_collection()
        rows_added = 0
        rows_skipped = 0

        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                item_name, category, location, unit, opening_qty, rate, reorder_level = row

                # 🔴 Skip empty item name
                if not item_name:
                    rows_skipped += 1
                    continue

                item_name = item_name.strip()
                opening_qty = float(opening_qty or 0)

                # ✅ DUPLICATE CHECK (HERE 👇)
                exists = inv_col.find_one({
                    "item_name": item_name,
                    "category": category,
                    "is_active": True
                })

                if exists:
                    rows_skipped += 1
                    continue  # ⛔ DO NOT INSERT DUPLICATE

                # ✅ INSERT NEW INVENTORY
                inv_col.insert_one({
                    "item_name": item_name,
                    "category": category,
                    "location": location,
                    "unit": unit,
                    "opening_qty": opening_qty,
                    "current_qty": opening_qty,
                    "rate": float(rate or 0),
                    "reorder_level": float(reorder_level or 0),
                    "is_active": True,
                    "created_at": datetime.now()
                })

                rows_added += 1

            except Exception as e:
                print(f"Row {idx} error:", e)
                rows_skipped += 1

        print("Added:", rows_added, "Skipped:", rows_skipped)
        return redirect("inv_app:inventory_master")

def inventory_template_download(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventory Template"

    # ✅ HEADER ROW
    headers = [
        "item_name",
        "category",
        "location",
        "unit",
        "opening_qty",
        "rate",
        "reorder_level"
    ]
    ws.append(headers)

    # ✅ SAMPLE ROW (optional but helpful)
    ws.append([
        "Marble White",
        "Tiles",
        "Godown-1",
        "SqFt",
        500,
        45,
        100
    ])

    # ✅ RESPONSE
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        'attachment; filename="inventory_bulk_template.xlsx"'
    )

    wb.save(response)
    return response

# Inventory Delete From Master
def inventory_master_delete(request, pk):
    col = get_inventory_master_collection()
    col.delete_one({"_id": ObjectId(pk)})
    print("inventory delete ...")
    return redirect("inv_app:inventory_master")

# Inventory Stock In
def inventory_ledger_view(request):
    inv_col = get_inventory_master_collection()
    ledger_col = get_inventory_ledger_collection()

    # 🔹 INVENTORY ITEMS (for dropdown)
    items = list(inv_col.find({"is_active": True}))
    for i in items:
        i["id"] = str(i["_id"])

    # 🔹 LEDGER RECORDS (IN + OUT)
    ledger = list(ledger_col.find().sort("created_at", -1))
    for l in ledger:
        l["id"] = str(l["_id"])

    # 🔹 STOCK IN SUBMIT
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        qty = float(request.POST.get("qty"))
        rate = float(request.POST.get("rate"))
        location = request.POST.get("location")
        remarks = request.POST.get("remarks", "")

        item = inv_col.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise Exception("Inventory item not found")

        # LEDGER IN
        ledger_col.insert_one({
            "item_id": item["_id"],
            "item_name": item["item_name"],
            "category": item.get("category"),
            "location": location,
            "qty": qty,
            "rate": rate,
            "amount": qty * rate,
            "txn_type": "IN",
            "source": "STOCK_IN",
            "remarks": remarks,
            "created_by": request.session.get("mongo_username"),
            "created_at": datetime.now()
        })

        # UPDATE MASTER
        inv_col.update_one(
            {"_id": item["_id"]},
            {"$inc": {"current_qty": qty}}
        )

        return redirect("inv_app:inventory_ledger")



    return render(request, "inv_app/inventory_ledger.html", {
        "items": items,
        "ledger": ledger
    })

# Inventory Stock In Reverse Entry
def delete_stock_in(request, ledger_id):
    inv_col = get_inventory_master_collection()
    ledger_col = get_inventory_ledger_collection()

    if request.method != "POST":
        raise Http404("Invalid request")

    # 🔹 1. FETCH ORIGINAL STOCK IN LEDGER
    ledger = ledger_col.find_one({
        "_id": ObjectId(ledger_id),
        "txn_type": "IN",
        "source": "STOCK_IN"
    })

    if not ledger:
        raise Http404("Stock IN entry not found")

    qty = float(ledger["qty"])
    item_id = ledger["item_id"]

    # 🔹 2. FETCH INVENTORY MASTER
    item = inv_col.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise Http404("Inventory item not found")

    # 🔹 3. CHECK SUFFICIENT STOCK (CRITICAL)
    if item["current_qty"] < qty:
        raise Exception("Cannot delete stock-in: stock already consumed")

    # 🔹 4. LEDGER ENTRY (REVERSAL → OUT)
    ledger_col.insert_one({
        "item_id": item["_id"],
        "item_name": item["item_name"],
        "category": item.get("category"),
        "location": ledger.get("location"),
        "qty": qty,
        "rate": ledger.get("rate", 0),
        "amount": qty * ledger.get("rate", 0),
        "txn_type": "OUT",
        "source": "STOCK_IN_REVERSE",
        "ref_id": ledger["_id"],
        "remarks": "Wrong stock-in entry reversed",
        "created_by": request.session.get("mongo_username"),
        "created_at": datetime.now()
    })

    # 🔹 5. UPDATE INVENTORY MASTER (DECREASE STOCK)
    inv_col.update_one(
        {"_id": item["_id"]},
        {"$inc": {"current_qty": -qty}}
    )

    return redirect("inv_app:inventory_ledger")





# Inventory Category Master
def category_master(request):
    col = category_collection()
    if request.method == "POST":
        name = request.POST.get("category_name")
        if name:
            col.insert_one({
                "category_name": name,
                "is_active": True,
                "created_at": datetime.now()
            })
        return redirect("inv_app:category_master")

    # categories = list(col.find({"is_active": True}))
    categories = list(col.find({"is_active": {"$ne": False}}))
    for c in categories:
        c["id"] = str(c["_id"])

    return render(
        request, "inv_app/category_master.html",
        {"categories": categories}
    )

# Inventory Category Delete
def category_delete(request, pk):
    col = category_collection()
    col.delete_one({"_id": ObjectId(pk)})
    return redirect("inv_app:category_master")



# already done in cnc order consume
# def add_order_inventory(request, order_id):
#     inv_col = get_inventory_master_collection()
#     ledger_col = get_inventory_ledger_collection()
#     order_inv_col = get_order_inventory_collection()
#
#     if request.method == "POST":
#         item_id = request.POST.get("item_id")
#         qty = float(request.POST.get("qty"))
#
#         item = inv_col.find_one({"_id": ObjectId(item_id)})
#         if not item:
#             raise Exception("Item not found")
#
#         if item["current_qty"] < qty:
#             raise Exception("Insufficient stock")
#
#         # 🔹 1. SAVE ORDER INVENTORY
#         order_inv_col.insert_one({
#             "order_id": ObjectId(order_id),
#             "item_id": item["_id"],
#             "item_name": item["item_name"],
#             "qty": qty,
#             "rate": item["rate"],
#             "total": qty * item["rate"],
#             "created_at": datetime.now()
#         })
#
#         # 🔹 2. LEDGER ENTRY (OUT)
#         ledger_col.insert_one({
#             "item_id": item["_id"],
#             "item_name": item["item_name"],
#             "location": item["location"],
#             "qty": qty,
#             "rate": item["rate"],
#             "amount": qty * item["rate"],
#             "txn_type": "OUT",
#             "source": "ORDER",
#             "ref_id": ObjectId(order_id),
#             "created_at": datetime.now()
#         })
#
#         # 🔹 3. UPDATE INVENTORY MASTER
#         inv_col.update_one(
#             {"_id": item["_id"]},
#             {"$inc": {"current_qty": -qty}}
#         )
#
#         return redirect("cnc_work_app:detail", pk=order_id)



