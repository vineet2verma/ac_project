from django.shortcuts import render
from .mongo import get_orders_collection
from cloudinary.uploader import upload

# Create your views here.
from django.utils.timezone import now
from datetime import datetime

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import ImageHandling, Order, DesignFile, MachineMaster, MachineDetail, Inventory
from .forms import MachineDetailForm

from django.db.models import Q, Sum
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
# Cloudinary


# CNC Order List
def cnc_order_list(request):
    order_collection = get_orders_collection()

    # ---------- GET ALL ORDERS ----------
    orders = list(order_collection.find().sort("created_at", -1))

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
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.title = request.POST.get("title")
        order.stone = request.POST.get("stone")
        order.color = request.POST.get("color")
        order.approval_date = request.POST.get("approval_date")
        order.exp_delivery_date = request.POST.get("exp_delivery_date")
        order.coverage_area = request.POST.get("coverage_area")
        order.party_name = request.POST.get("party_name")
        order.packing_instruction = request.POST.get("packing_instruction")
        order.sales_person = request.POST.get("sales_person")
        order.remarks = request.POST.get("remarks")

        # ---------------- SAFE IMAGE REPLACE ----------------
        old_public_id = None

        if request.FILES.get("image"):
            # 1️⃣ Save old image public_id
            if order.image:
                old_public_id = order.image.public_id

            # 2️⃣ Assign new image (upload happens on save)
            order.image = request.FILES["image"]

        # 3️⃣ Save order (Cloudinary upload happens here)
        with transaction.atomic():
            order.save()

        # 4️⃣ Delete old image ONLY after successful save
        if old_public_id:
            try:
                destroy(old_public_id)
            except Exception:
                pass  # log this if needed

        return redirect("cnc_work_app:detail", pk=order.id)
    return redirect("cnc_work_app:detail", pk=order.id)


def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST":
        # 🔥 Delete image from Cloudinary first (safe)
        if order.image:
            try:
                destroy(order.image.public_id)
            except Exception:
                pass  # production में log करें

        # 🔥 Delete order from DB
        order.delete()

        messages.success(request, "Order deleted successfully")
        return redirect("cnc_work_app:index")

    return render(request, "cnc_work_app/order_confirm_delete.html", {
        "order": order
    })


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
