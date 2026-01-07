
from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime, date
from cnc_work_app.mongo import *
from bson import ObjectId
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404
from cloudinary.uploader import upload, destroy

# Create your views here.


# Add Design File In Order
def add_design_file(request, pk):
    order_collection = get_orders_collection()
    design_collection = get_design_files_collection()

    # 🔹 Fetch order first
    order = order_collection.find_one({"_id": ObjectId(pk)})
    if not order:
        raise Http404("Order not found")

    if request.method == "POST":
        name = request.POST.get("name")
        file = request.FILES.get("file")

        if name and file:
            upload_result = upload(file,folder="design_files")

            design_collection.insert_one({
                "order_id": pk,                     # Mongo Order ID (string)
                "name": name,
                "file_url": upload_result["secure_url"],
                "public_id": upload_result["public_id"],
                "status": "pending",
                "created_by": request.session.get("mongo_username"),
                "created_at": datetime.utcnow(),
            })
            # 🔹 UPDATE ORDER STATUS
            order_collection.update_one(
                {"_id": ObjectId(pk)},
                {"$set": {"current_status": "Inventory Pending"}}
            )

    return redirect("cnc_work_app:detail", pk=pk)

# Add Design Action
def design_action(request, design_id, action):
    collection = get_design_files_collection()

    if action in ["approve", "cancel"]:
        collection.update_one(
            {"_id": ObjectId(design_id)},
            {"$set": {
                "status": "approved" if action == "approve" else "cancelled",
                "approved_at": datetime.utcnow()
            }}
        )

    return redirect(request.META.get("HTTP_REFERER", "/"))

# Design Delete
def design_delete(request, order_id, design_id):
    if request.method != "POST":
        raise Http404("Invalid request")

    design_col = get_design_files_collection()

    design_col.delete_one({
        "_id": ObjectId(design_id),
        "order_id": order_id
    })

    return redirect("cnc_work_app:detail", pk=order_id)
