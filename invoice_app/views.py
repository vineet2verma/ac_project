from django.http import HttpResponse
from django.shortcuts import render, redirect
from datetime import datetime
import uuid
from django.conf import settings
# Mongo db
from cnc_work_app.mongo import *


# Create your views here.

def invoice_list(request):
    invoices = list(invoice_collection().find().sort("created_at", -1))
    return render(
        request, "invoice_app/invoice_list.html",
        {"invoices": invoices}
    )


def create_invoice(request):
    if request.method == "POST":
        image_path = None

        if request.FILES.get("image"):
            img = request.FILES["image"]
            img_name = f"{uuid.uuid4()}_{img.name}"
            img_path = os.path.join(settings.MEDIA_ROOT, "invoices", img_name)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)

            with open(img_path, "wb+") as f:
                for chunk in img.chunks():
                    f.write(chunk)

            image_path = f"invoices/{img_name}"

        invoice_collection().insert_one({
            "invoice_no": request.POST.get("invoice_no"),
            "client_name": request.POST.get("client_name"),
            "description": request.POST.get("description"),
            "amount": float(request.POST.get("amount")),
            "image": image_path,
            "created_at": datetime.now()
        })

        return redirect("design_app:invoice_list")

    return render(request, "invoice_app/create_invoice.html")
