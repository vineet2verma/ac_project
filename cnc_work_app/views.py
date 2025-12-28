# Create your views here.
from django.utils.timezone import now
from datetime import datetime
from django.db.models import Q, Sum
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
# Models
from .models import ImageHandling, Order, DesignFile, MachineMaster, MachineDetail, Inventory
# Forms
from .forms import MachineDetailForm
# Cloudinary
from cloudinary.uploader import upload
from cloudinary.uploader import upload, destroy
# Mongo db
from .mongo import get_orders_collection
from bson import ObjectId


# CNC Order List
def cnc_order_list(request):
    order_collection = get_orders_collection()

    # ---------- GET ALL ORDERS ----------
    orders = list(order_collection.find().sort("created_at", -1))

    # 🔥 VERY IMPORTANT: Mongo _id → id (string)
    for o in orders:
        o["id"] = str(o["_id"])

    # ---------- SEARCH & FILTER ----------
    q = request.GET.get("q")
    status = request.GET.get("status")  # optional
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    if q:
        orders = [
            o for o in orders
        if q.lower() in (o.get("stone", "").lower())
               or q.lower() in (o.get("color", "").lower())
               or q.lower() in (o.get("party_name", "").lower())
               or q.lower() in (o.get("sales_person", "").lower())
               or q.lower() in (o.get("title", "").lower())
        ]

        # ---------- DATE FILTER ----------
    if from_date:
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
        orders = [o for o in orders if o.get("approval_date") and o["approval_date"] >= from_date]

    if to_date:
        to_date = datetime.strptime(to_date, "%Y-%m-%d")
        orders = [o for o in orders if o.get("approval_date") and o["approval_date"] <= to_date]

        # ---------- PAGINATION ----------
    per_page = request.GET.get("per_page", 5)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 5

    paginator = Paginator(orders, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "images": page_obj,  # keeping same variable name for template
        "page_obj": page_obj,
        "per_page": per_page,
    }

    return render(request, "cnc_work_app/cnc_order_list.html", context)

# Add Order
def add_order(request):
    order_collection = get_orders_collection()
    if request.method == 'POST':
        # ---------- IMAGE  ----------
        image_url = None  # ✅ SAME variable name
        if request.FILES.get("image"):
            result = upload(
                request.FILES["image"],
                folder="orders"
            )
            image_url = result.get("secure_url")

        # ---------- DATES (FIX) ----------
        approval_date = request.POST.get('approval_date')
        exp_delivery_date = request.POST.get('exp_delivery_date')

        approval_date_obj = (
            datetime.strptime(approval_date, "%Y-%m-%d")
            if approval_date else None
        )

        exp_delivery_date_obj = (
            datetime.strptime(exp_delivery_date, "%Y-%m-%d")
            if exp_delivery_date else None
        )

        data = {
            'title' : request.POST.get('title'),
            'image' : image_url,
            'stone' : request.POST.get('stone'),
            'color' : request.POST.get('color'),
            'remarks' : request.POST.get('remarks'),
            'packing_instruction' : request.POST.get('packing_instruction'),
            'coverage_area' : request.POST.get('coverage_area'),
            'party_name' : request.POST.get('party_name'),
            'sales_person' : request.POST.get('sales_person'),
            'created_at' : datetime.now(),
            'approval_date' : approval_date_obj,
            'exp_delivery_date' : exp_delivery_date_obj,
        }
        order_collection.insert_one(data)

    return redirect('cnc_work_app:index')

def order_edit(request, pk):
    order_collection = get_orders_collection()

    # 🔹 Fetch existing order from MongoDB
    order = order_collection.find_one({"_id": ObjectId(pk)})

    if not order:
        return redirect("cnc_work_app:index")

    if request.method == "POST":

        # ---------- DATE FIX ----------
        approval_date = request.POST.get("approval_date")
        exp_delivery_date = request.POST.get("exp_delivery_date")

        approval_date_obj = (
            datetime.strptime(approval_date, "%Y-%m-%d")
            if approval_date else None
        )

        exp_delivery_date_obj = (
            datetime.strptime(exp_delivery_date, "%Y-%m-%d")
            if exp_delivery_date else None
        )

        # ---------- IMAGE UPDATE ----------
        image_url = order.get("image")   # existing image
        old_public_id = None

        if request.FILES.get("image"):
            # extract public_id from old image URL
            if image_url:
                try:
                    old_public_id = image_url.split("/")[-1].split(".")[0]
                except Exception:
                    old_public_id = None

            # upload new image
            result = upload(
                request.FILES["image"],
                folder="orders"
            )
            image_url = result.get("secure_url")

        # ---------- UPDATE DATA ----------
        update_data = {
            "title": request.POST.get("title"),
            "stone": request.POST.get("stone"),
            "color": request.POST.get("color"),
            "approval_date": approval_date_obj,
            "exp_delivery_date": exp_delivery_date_obj,
            "coverage_area": request.POST.get("coverage_area"),
            "party_name": request.POST.get("party_name"),
            "packing_instruction": request.POST.get("packing_instruction"),
            "sales_person": request.POST.get("sales_person"),
            "remarks": request.POST.get("remarks"),
            "image": image_url,
            "updated_at": datetime.now(),
        }

        order_collection.update_one(
            {"_id": ObjectId(pk)},
            {"$set": update_data}
        )

        # ---------- DELETE OLD IMAGE (SAFE) ----------
        if old_public_id:
            try:
                destroy(f"orders/{old_public_id}")
            except Exception:
                pass

    return redirect("cnc_work_app:detail", pk=str(pk))

def order_delete(request, pk):
    order_collection = get_orders_collection()

    # 🔹 Fetch order from MongoDB
    order = order_collection.find_one({"_id": ObjectId(pk)})

    if not order:
        messages.error(request, "Order not found")
        return redirect("cnc_work_app:index")

    if request.method == "POST":

        # 🔥 Delete image from Cloudinary (SAFE)
        image_url = order.get("image")
        if image_url:
            try:
                # extract public_id from URL
                public_id = image_url.split("/")[-1].split(".")[0]
                destroy(f"orders/{public_id}")
            except Exception:
                pass  # production में logger use करें

        # 🔥 Delete order from MongoDB
        order_collection.delete_one({"_id": ObjectId(pk)})

        messages.success(request, "Order deleted successfully")
        return redirect("cnc_work_app:index")

    return render(
        request,
        "cnc_work_app/order_confirm_delete.html",
        {"order": order}
    )


# For Image Handling
def add_image(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        myfile = request.FILES.get('image')
        if title and myfile:
            obj = ImageHandling(title=title, image=myfile)
            obj.save()
            return redirect('cnc_work_app:index')
        return redirect('cnc_work_app:index')


# Order detail page
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)

    design_files = DesignFile.objects.filter(order=order)
    machines_mast = MachineMaster.objects.all()
    machines = MachineDetail.objects.filter(order=order).order_by('-id')
    inventory = Inventory.objects.filter(order=order)
    machine_form = MachineDetailForm()

    # Machine Total Working Hours
    machines = MachineDetail.objects.filter(order=order)
    total_hours = machines.aggregate(total=Sum("working_hour"))["total"] or 0

    return render(request, "cnc_work_app/detail.html", {
        "order": order,
        "design_files": design_files,
        "inventory": inventory,
        "machines_mast": machines_mast,
        "machines": machines,
        "machine_form": machine_form,  # ✅ IMPORTANT
        "total_hours": total_hours,
    })


# Design Section
# Add Design File
def add_design_file(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name")
        file = request.FILES.get("file")

        if name and file:
            DesignFile.objects.create(order=order, name=name, file=file)

    return redirect("cnc_work_app:detail", pk=order.id)


# design file action
def design_file_action(request, pk, action):
    design = get_object_or_404(DesignFile, pk=pk)

    if action == "approve":
        design.status = "approved"
        design.approved_at = now()

    elif action == "cancel":
        design.status = "cancelled"
        design.approved_at = now()

    design.save()

    return JsonResponse({
        "status": design.status,
        "approved_at": design.approved_at.strftime("%d %b %Y %I:%M %p")
    })


# Inventory
# Add Inventory Item
def add_inventory(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        item_name = request.POST.get("item_name")
        qty = request.POST.get("qty")
        amount = request.POST.get("amount")
        if item_name and qty and amount:
            Inventory.objects.create(order=order, item_name=item_name, qty=qty, amount=amount)
        return redirect("cnc_work_app:detail", pk=order.id)


# Machine


# Add Machine Detail
def machine_add_update(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    if request.method == "POST":
        machine_id = request.POST.get("machine_id")
        if machine_id:
            machine = get_object_or_404(MachineDetail, id=machine_id, order=order)
            form = MachineDetailForm(request.POST, instance=machine)
        else:
            form = MachineDetailForm(request.POST)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.order = order
            obj.save()



        return redirect("cnc_work_app:detail", pk=order.id)


def machine_delete(request, order_id, pk):
    machine = get_object_or_404(
        MachineDetail,
        id=pk,
        order_id=order_id
    )

    if request.method == "POST":
        machine.delete()

    return redirect("cnc_work_app:detail", pk=order_id)


# Machine Master
# READ (LIST)
def machine_mast_list(request):
    machines = MachineMaster.objects.all()
    return render(request, "machine_mast/machine_list.html", {"machines": machines})
