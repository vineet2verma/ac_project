from django.contrib import messages
import openpyxl
from datetime import datetime, date
from bson import ObjectId
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from cnc_work_app.mongo import  *
from django.http import Http404



########## Inventory Master ##########
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
##########  ##########
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
########## Inventory templete  ##########
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

########## Inventory Delete From Master ##########
def inventory_master_delete(request, pk):
    col = get_inventory_master_collection()
    col.delete_one({"_id": ObjectId(pk)})
    return redirect("inv_app:inventory_master")

########## Inventory Stock In ##########
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

########## Inventory Stock In Reverse Entry ##########
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


########## Add Inventory In Order ##########
def add_order_inventory(request, order_id):
    inv_master_col = get_inventory_master_collection()
    order_inv_col = get_order_inventory_collection()
    order_col = get_orders_collection()
    ledger_col = get_inventory_ledger_collection()

    if request.method != "POST": return redirect("cnc_work_app:detail", pk=order_id)

    inventory_id = request.POST.get("inventory_id")
    qty = float(request.POST.get("qty", 0))

    if not inventory_id or qty <= 0:
        raise Http404("Invalid inventory input")

    # 🔹 Fetch order from MongoDB
    order = order_col.find_one({"_id": ObjectId(order_id)})
    if not order: raise Http404("Order not found")
    inv = inv_master_col.find_one({"_id": ObjectId(inventory_id)})
    if not inv: raise Http404("Inventory item not found")

    # available_qty = float(inv.get("current_qty", 0))
    # rate = float(inv.get("rate", 0))
    # order_title = order.get("title", "Order")
    # sales_person = order.get("sales_person", "-")
    # remarks_text = f"Order: {order_title} | Sales: {sales_person}"

    # ================= SAVE ORDER INVENTORY =================
    order_inv_col.insert_one({
        "order_id": order_id,  # string
        "inventory_id": inventory_id,  # string
        "item_name": inv["item_name"],
        "required_qty": qty,
        "reserved_qty": 0,
        "status": "PENDING",
        "rate": float(inv.get("rate", 0)),
        "created_by": request.session["mongo_username"],
        "created_at": datetime.now()
    })
    return redirect("cnc_work_app:detail", pk=order_id)




########## INVENTORY CHECK (AVAILABLE / SHORTAGE) ##########
def inventory_check(request, order_id):

    order_inv_col = get_order_inventory_collection()
    inv_master_col = get_inventory_master_collection()

    records = list(order_inv_col.find({
        "order_id": ObjectId(order_id)
    }))

    for r in records:
        item = inv_master_col.find_one({
            "_id": ObjectId(r["inventory_id"])
        })

        if not item:
            r["status_calc"] = "INVALID"
            r["available_qty"] = 0
            r["shortage_qty"] = r["required_qty"]
        else:
            available = float(item.get("current_qty", 0))

            if available >= r["required_qty"]:
                r["status_calc"] = "AVAILABLE"
                r["shortage_qty"] = 0
            else:
                r["status_calc"] = "SHORTAGE"
                r["shortage_qty"] = r["required_qty"] - available

            r["available_qty"] = available
            r["item_name"] = item.get("item_name")

        r["id"] = str(r["_id"])

    return render(request, "inv_app/inventory_check.html", {
        "records": records,
        "order_id": order_id
    })


########## RESERVE STOCK (AVAILABLE) ##########
def inventory_reserve(request, inv_id):

    order_inv_col = get_order_inventory_collection()
    inv_master_col = get_inventory_master_collection()
    ledger_col = get_inventory_ledger_collection()

    rec = order_inv_col.find_one({"_id": ObjectId(inv_id)})
    if not rec:
        raise Http404("Order inventory record not found")

    # ❌ Already reserved → block
    if rec.get("status") == "RESERVED":
        raise Http404("Inventory already reserved")

    item = inv_master_col.find_one({
        "_id": ObjectId(rec["inventory_id"])
    })
    if not item:
        raise Http404("Inventory item not found")

    available_qty = float(item.get("current_qty", 0))
    required_qty = float(rec.get("required_qty", 0))

    if available_qty < required_qty:
        raise Http404("Stock insufficient for reservation")

    # 🔒 LOCK STOCK (DEDUCT FROM AVAILABLE)
    inv_master_col.update_one(
        {"_id": item["_id"]},
        {"$inc": {"current_qty": -required_qty}}
    )

    # 🔐 UPDATE ORDER INVENTORY
    order_inv_col.update_one(
        {"_id": rec["_id"]},
        {"$set": {
            "reserved_qty": required_qty,
            "status": "RESERVED",
            "reserved_at": datetime.now()
        }}
    )

    # 📒 LEDGER ENTRY (RESERVE, NOT OUT)
    ledger_col.insert_one({
        "item_id": item["_id"],
        "item_name": item.get("item_name"),
        "order_id": rec["order_id"],
        "qty": required_qty,
        "txn_type": "RESERVE",
        "ref_type": "ORDER",
        "ref_id": rec["_id"],
        "created_at": datetime.now()
    })

    return redirect(request.META.get("HTTP_REFERER"))


########## ❌ SHORTAGE → PURCHASE REQUISITION ##########
def create_purchase_requisition(request, inv_id):

    order_inv_col = get_order_inventory_collection()
    inv_master_col = get_inventory_master_collection()
    pr_col = get_purchase_requisition_collection()

    inv = order_inv_col.find_one({"_id": ObjectId(inv_id)})
    if not inv:
        raise Http404("Order inventory record not found")

    # 🔒 Prevent duplicate PR
    if inv.get("status") == "PR_CREATED":
        raise Http404("Purchase requisition already created")

    item = inv_master_col.find_one({
        "_id": ObjectId(inv["inventory_id"])
    })
    if not item:
        raise Http404("Inventory master item not found")

    available_qty = float(item.get("current_qty", 0))
    required_qty = float(inv.get("required_qty", 0))

    if available_qty >= required_qty:
        raise Http404("No shortage exists for this item")

    shortage_qty = required_qty - available_qty

    # 📝 CREATE PURCHASE REQUISITION
    pr_col.insert_one({
        "order_id": inv["order_id"],
        "order_inventory_id": inv["_id"],
        "inventory_id": inv["inventory_id"],
        "item_name": inv.get("item_name"),
        "required_qty": shortage_qty,
        "status": "PR_CREATED",
        "created_at": datetime.now()
    })

    # 🔁 UPDATE ORDER INVENTORY STATUS
    order_inv_col.update_one(
        {"_id": inv["_id"]},
        {"$set": {
            "status": "PR_CREATED",
            "shortage_qty": shortage_qty
        }}
    )

    return redirect(request.META.get("HTTP_REFERER"))


def pr_list(request, order_id):

    prs = list(
        get_purchase_requisition_collection().find(
            {"order_id": ObjectId(order_id)}
        ).sort("created_at", -1)
    )

    for pr in prs:
        pr["id"] = str(pr["_id"])

    return render(request, "inv_app/pr_list.html", {
        "prs": prs,
        "order_id": order_id
    })

def material_received(request, pr_id):

    pr_col = get_purchase_requisition_collection()
    order_inv_col = get_order_inventory_collection()
    inv_master_col = get_inventory_master_collection()
    ledger_col = get_inventory_ledger_collection()

    pr = pr_col.find_one({"_id": ObjectId(pr_id)})
    if not pr:
        raise Http404("Purchase requisition not found")

    # 🔒 Prevent double receive
    if pr.get("status") == "RECEIVED":
        raise Http404("Material already received")

    inv = order_inv_col.find_one({"_id": ObjectId(pr["order_inventory_id"])})
    if not inv:
        raise Http404("Order inventory record not found")

    # 📦 STOCK IN
    inv_master_col.update_one(
        {"_id": ObjectId(pr["inventory_id"])},
        {"$inc": {"current_qty": float(pr["required_qty"])}}
    )

    # 📝 UPDATE PR STATUS
    pr_col.update_one(
        {"_id": pr["_id"]},
        {"$set": {
            "status": "RECEIVED",
            "received_at": datetime.now()
        }}
    )

    # 🔁 ORDER INVENTORY BACK TO AVAILABLE
    order_inv_col.update_one(
        {"_id": inv["_id"]},
        {"$set": {"status": "AVAILABLE"}}
    )

    # 📒 LEDGER ENTRY (IN)
    ledger_col.insert_one({
        "item_id": ObjectId(pr["inventory_id"]),
        "item_name": pr.get("item_name"),
        "order_id": pr["order_id"],
        "qty": float(pr["required_qty"]),
        "txn_type": "IN",
        "ref_type": "PR",
        "ref_id": pr["_id"],
        "created_at": datetime.now()
    })

    return redirect("inv_app:check", order_id=str(inv["order_id"]))


########## Delete Inventory From Order (ERP FINAL) ##########
def delete_order_inventory(request, order_id, inv_id):
    order_inv_col = get_order_inventory_collection()
    inv_master_col = get_inventory_master_collection()
    ledger_col = get_inventory_ledger_collection()
    order_col = get_orders_collection()

    if request.method != "POST":
        return redirect("cnc_work_app:detail", pk=order_id)

    # 🔹 1. Fetch order inventory record
    order_inv = order_inv_col.find_one({
        "_id": ObjectId(inv_id),
        "order_id": order_id  # string
    })

    if not order_inv:
        raise Http404("Inventory item not found")

    inventory_id = order_inv["inventory_id"]  # string
    qty = float(order_inv.get("qty", 0))

    inv = inv_master_col.find_one({"_id": ObjectId(inventory_id)})
    if not inv:
        raise Http404("Inventory master item not found")

    rate = float(inv.get("rate", 0))

    # 🔹 2. FETCH ORDER DETAILS (FOR REMARKS)
    order = order_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise Http404("Order not found")

    order_title = order.get("title", "Order")
    sales_person = order.get("sales_person", "-")

    remarks_text = f"Order: {order_title} | Sales: {sales_person}"

    # ================= LEDGER ENTRY (IN - REVERSAL) =================
    ledger_col.insert_one({
        "item_id": inv["_id"],
        "item_name": inv["item_name"],
        "category": inv.get("category"),
        "location": inv.get("location"),
        "qty": qty,
        "rate": rate,
        "amount": qty * rate,
        "txn_type": "IN",
        "source": "ORDER_REVERSE",
        "ref_id": order_id,
        "remarks": remarks_text,

        # 🔐 USER AUDIT
        "created_by_id": request.session.get("mongo_user_id"),
        "created_by": request.session.get("mongo_username"),
        "created_at": datetime.now()
    })

    # ================= UPDATE MASTER STOCK =================
    inv_master_col.update_one(
        {"_id": inv["_id"]},
        {"$inc": {"current_qty": qty}}
    )

    # ================= DELETE ORDER INVENTORY =================
    order_inv_col.delete_one({"_id": ObjectId(inv_id)})

    return redirect("cnc_work_app:detail", pk=order_id)






########## Inventory Category Master ##########
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

########## Inventory Category Delete ##########
def category_delete(request, pk):
    col = category_collection()
    col.delete_one({"_id": ObjectId(pk)})
    return redirect("inv_app:category_master")









