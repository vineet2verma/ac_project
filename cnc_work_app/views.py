# Create your views here.
from datetime import datetime, date
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404
# Cloudinary
from cloudinary.uploader import upload, destroy
from bson import ObjectId
# Mongo db
from .mongo import (get_orders_collection,
                    get_design_files_collection,
                    get_machine_master_collection,get_machine_work_collection,
                    get_inventory_master_collection,
                    get_order_inventory_collection,
                    get_quality_collection, get_dispatch_collection,
                    get_inventory_ledger_collection,
                    category_collection,
                    )

# CNC Order List
def cnc_order_list(request):
    order_collection = get_orders_collection()

    page = int(request.GET.get("page", 1))
    per_page = int(request.GET.get("per_page", 10))
    skip = (page - 1) * per_page

    query = {}

    q = request.GET.get("q")
    status = request.GET.get("status")
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    if q:
        query["$or"] = [
            {"stone": {"$regex": q, "$options": "i"}},
            {"color": {"$regex": q, "$options": "i"}},
            {"party_name": {"$regex": q, "$options": "i"}},
            {"sales_person": {"$regex": q, "$options": "i"}},
            {"title": {"$regex": q, "$options": "i"}},
        ]

    if status:
        query["status"] = status

    if from_date or to_date:
        query["approval_date"] = {}
        if from_date:
            query["approval_date"]["$gte"] = datetime.strptime(from_date, "%Y-%m-%d")
        if to_date:
            query["approval_date"]["$lte"] = datetime.strptime(to_date, "%Y-%m-%d")

    total_count = order_collection.count_documents(query)

    orders = list(
        order_collection.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(per_page)
    )

    for o in orders:
        o["id"] = str(o["_id"])

    paginator = Paginator(range(total_count), per_page)
    page_obj = paginator.get_page(page)

    return render(request, "cnc_work_app/cnc_order_list.html", {
        "images": orders,
        "page_obj": page_obj,
        "per_page": per_page,
        "total": total_count
    })

# Order Session
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
            'current_status' : "Design Pending",
        }
        order_collection.insert_one(data)

    return redirect('cnc_work_app:index')

# Edit Order
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
# Delete Order
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
# Order detail page
def order_detail(request, pk):
    order_col = get_orders_collection()
    design_col = get_design_files_collection()
    machine_master_col = get_machine_master_collection()
    machine_work_col = get_machine_work_collection()
    inv_master_col = get_inventory_master_collection()
    order_inv_col = get_order_inventory_collection()
    qc_col = get_quality_collection()
    dispatch_col = get_dispatch_collection()

    # ---------------- ORDER ----------------
    order = order_col.find_one({"_id": ObjectId(pk)})
    if not order:
        raise Http404("Order not found")
    order["id"] = str(order["_id"])

    # ---------------- DESIGN FILES ----------------
    design_files = list(design_col.find({"order_id": pk}).sort("created_at", -1))
    for f in design_files:
        f["id"] = str(f["_id"])

    # ----------------- INVENTORY MASTER (Dropdown) -----------------

    inventory_items = list(inv_master_col.find({"is_active": True}))

    for i in inventory_items:
        i["id"] = str(i["_id"])  # 🔥 VERY IMPORTANT

    # ----------------- ORDER INVENTORY (TABLE) -----------------
    order_inventory = list(order_inv_col.find({"order_id": pk}))
    print(f"order inv :  {order_inventory}")
    for oi in order_inventory:
        oi["id"] = str(oi["_id"])

    # ---------------- MACHINE MASTER (Dropdown) ----------------
    machines_mast = list(machine_master_col.find({"is_active": True}))
    for m in machines_mast:
        m["id"] = str(m["_id"])   # ✅ for dropdown

    # ---------------- MACHINE WORK (Table + Delete/Edit) ----------------
    machines = list(machine_work_col.find({"order_id": pk}).sort("created_at", -1))

    total_hours = 0
    for m in machines:
        m["id"] = str(m["_id"])                # 🔥 MOST IMPORTANT LINE
        m["machine_date"] = m.get("date")      # safe mapping
        total_hours += float(m.get("working_hour", 0))

    # ---------------------- QUALITY CHECK  ----------------------
    quality_checks = list(qc_col.find({"order_id": pk}).sort("created_at", -1))
    for q in quality_checks:
        q["id"] = str(q["_id"])

    #  ---------------------- DISPATCH  ----------------------
    dispatches = list(dispatch_col.find({"order_id": pk}).sort("created_at", -1))
    for d in dispatches:
        d["id"] = str(d["_id"])




    # ---------------- RENDER ----------------
    return render(request, "cnc_work_app/detail.html", {
        "order": order,
        "design_files": design_files,
        # Inventory
        "inventory_items": inventory_items,
        "order_inventory": order_inventory,  # table
        # Machine
        "machines_mast": machines_mast,
        "machines": machines,
        "total_hours": total_hours,
        # QC + Dispatch
        "quality_checks": quality_checks,
        "dispatches": dispatches,
    })


# Design Session
# Add Design File
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

    return redirect("cnc_work_app:order_detail", pk=order_id)

# Quality & Dispatch Session
# Order Quality Check
def add_quality_check(request, order_id):
    if request.method == "POST":
        qc_collection = get_quality_collection()
        orders_collection = get_orders_collection()

        qc_collection.insert_one({
            "order_id": order_id,
            "checked_by": request.POST.get("checked_by"),
            "status": request.POST.get("status"),
            "remarks": request.POST.get("remarks"),
            "checked_at": datetime.utcnow(),
        })

        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "current_status": "Dispatch Pending"
            }}
        )

    return redirect("cnc_work_app:detail", pk=order_id)

# Order Dispatches
def add_dispatch(request, order_id):
    order_collection = get_orders_collection()
    dispatch_collection = get_dispatch_collection()  # 👈 aapko ye function banana hoga

    # 🔹 Fetch order from MongoDB
    order = order_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise Http404("Order not found")

    # 🔒 SAFETY: Prevent double dispatch
    if order.get("current_status") == "COMPLETED":
        raise Http404("Order already dispatched")

    if request.method == "POST":
        # 🔹 Insert dispatch record
        dispatch_collection.insert_one({
            "order_id": ObjectId(order_id),
            "vehicle_no": request.POST.get("vehicle_no"),
            "lr_no": request.POST.get("lr_no"),
            "dispatch_date": request.POST.get("dispatch_date"),
            "dispatched_by": request.POST.get("dispatched_by"),
            "remarks": request.POST.get("remarks"),
            "created_at": datetime.now()
        })

        # 🔹 Update order status
        order_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "current_status": "Complete",
                "dispatched_at": datetime.now()
            }}
        )

    return redirect("cnc_work_app:detail", pk=order_id)


# Add Machine For Order Work
def add_machine_work(request, order_id):
    if request.method == "POST":
        machine_id = request.POST.get("machine_id")
        work_type = request.POST.get("work_type", "ONTIME")
        working_hour = float(request.POST.get("working_hour"))
        operator = request.POST.get("operator")
        remarks = request.POST.get("remarks")

        master_col = get_machine_master_collection()
        machine = master_col.find_one({"_id": ObjectId(machine_id)})

        work_col = get_machine_work_collection()
        work_col.insert_one({
            "order_id": order_id,
            "machine_id": machine_id,
            "machine_name": machine["machine_name"],
            "work_type": work_type,
            "work_date": date.today().isoformat(),   # ✅ default today
            "working_hour": working_hour,
            "operator": operator,
            "remarks": remarks,
            "created_at": datetime.utcnow()
        })

    return redirect("cnc_work_app:detail", pk=order_id)


# # Machine Master
# ================= MACHINE MASTER LIST =================
def machine_master(request):
    col = get_machine_master_collection()
    machines = list(col.find().sort("created_at", -1))
    # Mongo _id → string for template
    for m in machines: m["id"] = str(m["_id"])
    return render(request,"cnc_work_app/machine_master_add.html",{"machines": machines})

@require_POST
def machine_master_add(request):
    col = get_machine_master_collection()
    machine_name = request.POST.get("machine_name", "").strip()
    machine_code = request.POST.get("machine_code", "").strip()
    is_active = request.POST.get("is_active") == "on"
    if not machine_name or not machine_code: return redirect("machine_master")

    col.insert_one({
        "machine_name": machine_name,
        "machine_code": machine_code,
        "is_active": is_active,
        "created_at": timezone.now()
    })
    return redirect("cnc_work_app:machine_master")
# ================= TOGGLE ACTIVE / INACTIVE IN MASTER=================
@require_POST
def machine_master_toggle(request, pk):
    col = get_machine_master_collection()
    try:
        oid = ObjectId(pk)
    except Exception:
        return redirect("cnc_work_app:machine_master")

    machine = col.find_one({"_id": oid})
    if machine:
        col.update_one(
            {"_id": oid},
            {"$set": {"is_active": not machine.get("is_active", True)}}
        )

    return redirect("cnc_work_app:machine_master")

# ================= ADD MACHINE =================
# Active Machines For Dropdown in Detail Page
def get_active_machines():
    col = get_machine_master_collection()
    machines = list(col.find({"is_active": True}))
    for m in machines:
        m["id"] = str(m["_id"])
    return machines

# Machine Delete From Order -----
def machine_delete(request, order_id, machine_work_id):
    if request.method == "POST":
        col = get_machine_work_collection()
        col.delete_one({"_id": ObjectId(machine_work_id)})
    return redirect("cnc_work_app:detail", pk=order_id)

# Machine Edit In Order -----
def machine_edit(request, order_id, machine_work_id):
    col = get_machine_work_collection()

    if request.method == "POST":
        col.update_one(
            {"_id": ObjectId(machine_work_id)},
            {"$set": {
                "machine_id": request.POST.get("machine_id"),   # ✅ optional but correct
                "working_hour": float(request.POST.get("working_hour", 0)),
                "work_type": request.POST.get("work_type", "ONTIME"),  # ✅ FIX
                "operator": request.POST.get("operator"),
                "remarks": request.POST.get("remarks"),
            }}
        )

    return redirect("cnc_work_app:detail", pk=order_id)



# Add Inventory In Order
# Add Inventory In Order (ERP FINAL)
def add_order_inventory(request, order_id):
    inv_master_col = get_inventory_master_collection()
    order_inv_col = get_order_inventory_collection()
    ledger_col = get_inventory_ledger_collection()
    order_col = get_orders_collection()

    if request.method != "POST":
        return redirect("cnc_work_app:detail", pk=order_id)

    inventory_id = request.POST.get("inventory_id")
    qty = float(request.POST.get("qty", 0))

    # 🔴 SAFETY CHECKS
    if not inventory_id:
        raise Http404("Inventory item not selected")

    # 🔹 Fetch order from MongoDB
    order = order_col.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise Http404("Order not found")
    inv = inv_master_col.find_one({"_id": ObjectId(inventory_id)})
    if not inv:
        raise Http404("Inventory item not found")

    available_qty = float(inv.get("current_qty", 0))
    if qty > available_qty:
        raise Http404("Qty exceeds available stock")
    rate = float(inv.get("rate", 0))

    order_title = order.get("title", "Order")
    sales_person = order.get("sales_person", "-")
    remarks_text = f"Order: {order_title} | Sales: {sales_person}"

    # ================= SAVE ORDER INVENTORY =================
    order_inv_col.insert_one({
        "order_id": order_id,                     # string
        "inventory_id": inventory_id,             # string
        "item_name": inv["item_name"],
        "qty": qty,
        "rate": rate,
        "total": qty * rate,
        "created_at": datetime.now()
    })

    # ================= LEDGER ENTRY (OUT) =================
    ledger_col.insert_one({
        "item_id": inv["_id"],
        "item_name": inv["item_name"],
        "category": inv.get("category"),
        "location": inv.get("location"),
        "qty": qty,
        "rate": rate,
        "amount": qty * rate,
        "txn_type": "OUT",
        "source": "ORDER",
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
        {"$inc": {"current_qty": -qty}}
    )
    # 🔹 Update order status
    order_col.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "current_status": "QC Pending",
            "dispatched_at": datetime.now()
        }}
    )

    return redirect("cnc_work_app:detail", pk=order_id)

# Delete Inventory From Order (ERP FINAL)
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
        "order_id": order_id   # string
    })

    if not order_inv:
        raise Http404("Inventory item not found")

    inventory_id = order_inv["inventory_id"]   # string
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





