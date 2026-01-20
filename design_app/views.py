import traceback

import cloudinary
from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime, date
from cnc_work_app.mongo import *
from bson import ObjectId
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404
from cloudinary.uploader import upload, destroy
from accounts_app.views import mongo_login_required, mongo_role_required

# Add Design File In Order
@mongo_login_required
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


# Delete Design File From Order
@mongo_login_required
def design_action(request, design_id, action):
    try:
        if request.method != "POST": return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

        design_col = get_design_files_collection()
        order_col = get_orders_collection()

        design = design_col.find_one({"_id": ObjectId(design_id)})
        if not design: return JsonResponse({"success": False, "message": "Design not found"}, status=404)

        order_id = design.get("order_id")
        if not order_id: return JsonResponse({"success": False, "message": "Order not linked"}, status=400)

        if action != "approve": return JsonResponse({"success": False, "message": "Invalid action"}, status=400)

        now = datetime.utcnow()

        # ✅ Approved person details
        approved_by_user_id = request.session.get("mongo_user_id", "")
        approved_by_username = request.session.get("mongo_username", "")
        approved_by_roles = request.session.get("mongo_roles", [])

        user_doc = users_collection().find_one({"_id": ObjectId(approved_by_user_id)})
        approved_by_name = user_doc.get("full_name") if user_doc else approved_by_username

        # 1️⃣ Approve design
        design_col.update_one(
            {"_id": ObjectId(design_id)},
            {"$set":
                {
                    "status": "approved",
                    "approved_at": now,
                    "approved_by_id": approved_by_user_id,
                    "approved_by_name": approved_by_name,
                    "approved_by_role": approved_by_roles,
                }
            }
        )

        # 2️⃣ DESIGN → COMPLETE
        order_col.update_one(
            {"_id": ObjectId(order_id), "order_status.stage": "DESIGN"},
            {"$set": {"order_status.$.status": "COMPLETE", "order_status.$.updated_at": now}}
        )

        # 3️⃣ MACHINE → PENDING (if not exists)
        order_col.update_one(
            {
                "_id": ObjectId(order_id),
                "order_status": {"$not": {"$elemMatch": {"stage": "MACHINE"}}}
            },
            {
                "$push": {
                    "order_status": {
                        "stage": "MACHINE",
                        "status": "PENDING",
                        "updated_at": now
                    }
                }
            }
        )

        return JsonResponse({"success": True})

    except Exception:
        # print(traceback.format_exc())
        return JsonResponse({"success": False, "message": "Server error"}, status=500)




# Design Delete
@mongo_login_required
def design_delete(request, order_id, design_id):
    if request.method != "POST": raise Http404("Invalid request")
    design_col = get_design_files_collection()

    # 🔹 Fetch design first
    design = design_col.find_one({
        "_id": ObjectId(design_id),
        "order_id": order_id
    })

    if not design: raise Http404("Design not found")

    # 🔹 Delete image from Cloudinary
    public_id = design.get("public_id")
    if public_id:
        try: cloudinary.uploader.destroy(public_id)
        except Exception: pass

    design_col.delete_one({
        "_id": ObjectId(design_id),
        "order_id": order_id
    })

    return redirect("cnc_work_app:detail", pk=order_id)
