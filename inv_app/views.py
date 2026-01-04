from datetime import datetime, date
from bson import ObjectId
import openpyxl
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from cnc_work_app.mongo import (
    get_inventory_master_collection,
    category_collection,
)



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

    return render(request, "inventory/inventory_master.html", {
        "items": items,
        "categories": categories,
    })

# Inventory Delete From Master
def inventory_master_delete(request, pk):
    col = get_inventory_master_collection()
    col.delete_one({"_id": ObjectId(pk)})
    print("inventory delete ...")
    return redirect("inv_app:inventory_master")

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
        request, "category/category_master.html",
        {"categories": categories}
    )

# Inventory Category Delete
def category_delete(request, pk):
    col = category_collection()
    col.delete_one({"_id": ObjectId(pk)})
    return redirect("inv_app:category_master")
