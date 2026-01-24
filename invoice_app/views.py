# Mongo db
from cnc_work_app.mongo import *
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime
import uuid, os
from math import ceil
from bson import ObjectId
from django.conf import settings
# Cloudinary
from cloudinary.uploader import upload, destroy

# Create your views here.





# View All Quotation List
def quotation_list(request):
    page = int(request.GET.get("page", 1))
    per_page = 10
    skip = (page - 1) * per_page

    search = request.GET.get("search", "").strip()

    query = {}
    if search:
        query = {
            "$or": [
                {"quotation_no": {"$regex": search, "$options": "i"}},
                {"customer.name": {"$regex": search, "$options": "i"}},
                {"customer.phone": {"$regex": search, "$options": "i"}},
            ]
        }

    total = invoice_collection().count_documents(query)
    pages = max(1, ceil(total / per_page))

    raw_data = (
        invoice_collection()
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(per_page)
    )

    quotations = []
    for q in raw_data:
        q["id"] = str(q["_id"])   # ✅ SAFE FIELD
        quotations.append(q)

    return render(request, "invoice_app/quotation_list.html", {
        "quotations": quotations,
        "page": page,
        "pages": pages,
        "page_range": range(1, pages + 1),
        "search": search
    })


# Create Quotation
def quotation_create(request, customer_id=None):

    # ---------- DEMO CUSTOMER (replace with DB later) ----------
    customer = {
        "id": customer_id,
        "company": "ABC Pvt Ltd",
        "name": "Demo Client",
        "gstin": "07ABCDE1234F1Z5",
        "phone": "9999999999",
        "sales_person": "Rahul",
    }

    # ===================== POST =====================
    if request.method == "POST":

        # ---------- ITEMS ----------
        items = []

        descriptions = request.POST.getlist("description[]")
        sizes = request.POST.getlist("size[]")
        sqfts = request.POST.getlist("sqft[]")
        boxes = request.POST.getlist("qty_box[]")
        rates = request.POST.getlist("rate[]")
        amounts = request.POST.getlist("amount[]")
        images = request.FILES.getlist("image[]")

        print("IMAGES RECEIVED:", images)  # ✅ DEBUG

        for i in range(len(descriptions)):
            image_url = None

            # Upload image to Cloudinary (if exists)
            if i < len(images) and images[i]:
                try:
                    result = upload(
                        images[i],
                        folder="quotation_items",   # ☁️ Cloudinary folder
                        resource_type="image"
                    )
                    image_url = result.get("secure_url")
                    print("UPLOADED:", image_url)

                except Exception as e:
                    print("CLOUDINARY ERROR:", e)

            items.append({
                "description": descriptions[i],
                "size": sizes[i],
                "sqft": float(sqfts[i] or 0),
                "qty_box": float(boxes[i] or 0),
                "rate": float(rates[i] or 0),
                "amount": float(amounts[i] or 0),
                "image": image_url,   # ☁️ URL only
            })

        # ---------- SAVE QUOTATION ----------
        invoice_collection().insert_one({
            "quotation_no": f"QT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}",
            "date": datetime.now().strftime("%d-%m-%Y"),
            "customer": customer,
            "items": items,

            "charges": {
                "discount": float(request.POST.get("discount", 0)),
                "gst": float(request.POST.get("gst", 0)),
                "cutting": float(request.POST.get("cutting", 0)),
                "cartage": float(request.POST.get("cartage", 0)),
                "packing": float(request.POST.get("packing", 0)),
            },

            "subtotal": float(request.POST.get("subtotal", 0)),
            "grand_total": float(request.POST.get("grand_total", 0)),
            "created_at": datetime.now(),
        })

        messages.success(request, "Quotation created successfully")
        return redirect("invoice_app:quotation_list")

    # ===================== GET =====================
    return render(request,"invoice_app/image_invoice_sraga.html",{"customer": customer})


# View Single Quotation
def quotation_view(request, qid):
    quotation = invoice_collection().find_one(
        {"_id": ObjectId(qid)}
    )

    if not quotation:
        messages.error(request, "Quotation not found")
        return redirect("invoice_app:quotation_list")

    # 🔥 IMPORTANT FIX
    quotation["id"] = str(quotation["_id"])

    return render(request, "invoice_app/quotation_view.html", {
        "quotation": quotation
    })


def get_cloudinary_public_id(url):
    if not url:
        return None
    try:
        # remove version and extension
        parts = url.split("/upload/")[1]
        parts = parts.split(".")[0]

        # remove version folder (v123456)
        if parts.startswith("v"):
            parts = "/".join(parts.split("/")[1:])

        return parts
    except Exception:
        return None


# Delete Quotation
def quotation_delete(request, qid):
    quotation = invoice_collection().find_one(
        {"_id": ObjectId(qid)}
    )

    if not quotation:
        messages.error(request, "Quotation not found")
        return redirect("invoice_app:quotation_list")

    # ---------- DELETE CLOUDINARY IMAGES ----------
    for item in quotation.get("items", []):
        image_url = item.get("image")

        public_id = get_cloudinary_public_id(image_url)

        if public_id:
            try:
                destroy(public_id)
                print("DELETED FROM CLOUDINARY:", public_id)
            except Exception as e:
                print("CLOUDINARY DELETE ERROR:", e)

    # ---------- DELETE QUOTATION ----------
    invoice_collection().delete_one(
        {"_id": ObjectId(qid)}
    )

    messages.success(request, "Quotation deleted successfully")
    return redirect("invoice_app:quotation_list")