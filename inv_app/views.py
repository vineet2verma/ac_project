from datetime import datetime, date
from bson import ObjectId
from django.shortcuts import render, get_object_or_404, redirect
from cnc_work_app.mongo import (
    get_inventory_master_collection,
    category_collection,
    get_orders_collection,
    get_design_files_collection,
    get_machine_master_collection, get_machine_work_collection,
    get_order_inventory_collection,
    get_quality_collection, get_dispatch_collection,
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
