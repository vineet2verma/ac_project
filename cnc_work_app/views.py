# Create your views here.
from datetime import datetime, date
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
# Cloudinary
from cloudinary.uploader import upload, destroy
from bson import ObjectId
from accounts_app.views import mongo_login_required, mongo_role_required
# Mongo db
from .mongo import  *
# Permission
from utils.permissions import get_user_permissions

def is_order_complete(order_status):
    return order_status and all(s["status"] == "COMPLETE" for s in order_status)


def get_current_pending_stage(order_status):
    for s in order_status:
        if s["status"] == "PENDING":
            return s["stage"]
    return None


def get_order_display_status(order_status):
    if not order_status:
        return "Pending", "bg-danger"

    pending_stages = [
        s["stage"].title()
        for s in order_status
        if s.get("status") == "PENDING"
    ]

    # ✅ All stages complete
    if not pending_stages:
        return "Complete", "bg-success"

    # ✅ Multiple pending stages
    text = " + ".join(f"{stage} Pending" for stage in pending_stages)

    # Badge color logic
    if len(pending_stages) > 1:
        badge = "bg-danger"          # Multiple pending → red
    else:
        badge = "bg-warning text-dark"  # Single pending → yellow

    return text, badge

# Not working yet now
def custom_404(request, exception):
    print("=======>>>> <<<<=======")
    return render(request, "404.html", status=404)


# CNC Order List
@mongo_login_required
def cnc_order_list(request):
    order_collection = get_orders_collection()
    users_col = users_collection()

    # ================= SESSION DATA =================
    role = request.session.get("mongo_roles",[])
    access_scope = request.session.get("access_scope")
    user_work_types = request.session.get("work_type_access", [])
    username = request.session.get("mongo_username")

    is_admin_or_manager = any(r in ["ADMIN", "MANAGER"] for r in role)

    query = {}

    # ================= ACCESS SCOPE (ONLY SOURCE OF TRUTH) =================
    if access_scope == "OWN": query["sales_person"] = username
    elif access_scope == "ALL":  pass  # No restriction
    else: query["_id"] = None  # Safety fallback

    # ================= WORK TYPE ACCESS (SECURITY) =================
    # Admin / Manager can see all
    if role not in ["ADMIN", "MANAGER"]:
        if user_work_types:
            query["type_of_work"] = {"$in": user_work_types}
        # else:
            # query["_id"] = None  # user sees nothing

    # ================= QUICK STATUS FILTER =================
    quick_status = request.GET.get("quick_status", "pending")

    if quick_status == "complete":
        query["order_status"] = {
            "$not": {"$elemMatch": {"status": "PENDING"}}
        }
    else:
        query["order_status"] = {
            "$elemMatch": {"status": "PENDING"}
        }

    # ================= ADMIN / MANAGER SALES FILTER =================
    sales_filter = request.GET.get("sales_person")
    if sales_filter and is_admin_or_manager:
        query["sales_person"] = sales_filter

    # ================= ADMIN WORK TYPE FILTER (UI) =================
    type_of_work = request.GET.get("type_of_work")
    if type_of_work and is_admin_or_manager:
        query["type_of_work"] = type_of_work

    # ================= SEARCH =================
    q = request.GET.get("q")
    if q:
        query["$or"] = [
            {"stone": {"$regex": q, "$options": "i"}},
            {"color": {"$regex": q, "$options": "i"}},
            {"party_name": {"$regex": q, "$options": "i"}},
            {"sales_person": {"$regex": q, "$options": "i"}},
            {"title": {"$regex": q, "$options": "i"}},
        ]

    # ================= DATE FILTER =================
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    if from_date or to_date:
        date_query = {}
        if from_date:
            date_query["$gte"] = datetime.strptime(from_date, "%Y-%m-%d")
        if to_date:
            date_query["$lte"] = datetime.strptime(to_date, "%Y-%m-%d")
        query["approval_date"] = date_query

    # ================= PAGINATION =================
    page = int(request.GET.get("page", 1))
    per_page = int(request.GET.get("per_page", 10))
    skip = (page - 1) * per_page

    # ================= COUNT =================
    total_count = order_collection.count_documents(query)

    # ================= FETCH =================
    orders = list(
        order_collection.find(query)
        .sort([("created_at", -1)])
        .skip(skip)
        .limit(per_page)
    )

    for o in orders:
        o["id"] = str(o["_id"])

        # 🔥 COMPUTED STATUS (NEW)
        text, badge = get_order_display_status(o.get("order_status", []))
        o["display_status"] = text
        o["status_badge"] = badge

    # ================= SALES USERS =================
    sales_users = list(users_col.find(
        {"roles": "SALES", "is_active": True},
        {"username": 1, "full_name": 1}
    ))

    # ================= PAGINATOR =================
    paginator = Paginator(range(total_count), per_page)
    page_obj = paginator.get_page(page)

    # ================= PERMISSIONS =================
    permissions = get_user_permissions(request)

    context = {
        "images": orders,
        "page_obj": page_obj,
        "per_page": per_page,
        "total": total_count,
        "sales_users": sales_users,
        "quick_status": quick_status,

        "can_qc": permissions["qc"],
        "can_dispatch": permissions["dispatch"],
        "can_inventory": permissions["inventory"],
        "can_sales": permissions["sales"],
        "can_production": permissions["production"],
        "is_admin": permissions["override"],
    }

    return render(request, "cnc_work_app/cnc_order_list.html", context)


# Add Order
@mongo_login_required
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

        # ---------- INITIAL ORDER STATUS ARRAY ----------
        order_status = [
            {
                "stage": "DESIGN",
                "status": "PENDING",
                "updated_at": datetime.now()
            },
            {
                "stage": "INVENTORY",
                "status": "PENDING",
                "updated_at": datetime.now()
            }
        ]

        packing_instruction = request.POST.getlist('packing_instruction[]')
        packing_instruction_str = ", ".join(packing_instruction)

        data = {
            'title': request.POST.get('title'),
            'image': image_url,
            'stone': request.POST.get('stone'),
            'color': request.POST.get('color'),
            'remarks': request.POST.get('remarks'),
            'packing_instruction': packing_instruction_str,
            'coverage_area': request.POST.get('coverage_area'),
            'party_name': request.POST.get('party_name'),
            'sales_person': request.POST.get('sales_person'),
            'type_of_work': request.POST.get('type_of_work'),
            'created_at': datetime.now(),
            'approval_date': approval_date_obj,
            'exp_delivery_date': exp_delivery_date_obj,
            'current_status': "Design Pending",
            "order_status": order_status,
        }
        order_collection.insert_one(data)

    return redirect('cnc_work_app:index')


# Edit Order
@mongo_login_required
def order_edit(request, pk):
    order_collection = get_orders_collection()

    # 🔹 Fetch existing order
    order = order_collection.find_one({"_id": ObjectId(pk)})
    order["id"] = str(order["_id"])

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
        image_url = order.get("image")
        old_public_id = None

        if request.FILES.get("image"):
            if image_url:
                try:
                    old_public_id = image_url.split("/")[-1].split(".")[0]
                except Exception:
                    old_public_id = None

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
            'type_of_work': request.POST.get('type_of_work'),
            "remarks": request.POST.get("remarks"),
            "image": image_url,
            "updated_at": datetime.now(),
        }

        order_collection.update_one(
            {"_id": ObjectId(pk)},
            {"$set": update_data}
        )

        # ---------- DELETE OLD IMAGE ----------
        if old_public_id:
            try:
                destroy(f"orders/{old_public_id}")
            except Exception:
                pass

        return redirect("cnc_work_app:detail", pk=str(pk))

    # ✅ IMPORTANT: RENDER EDIT PAGE ON GET
    return render(
        request,
        "cnc_work_app/order_edit.html",
        {"order": order}
    )


# Delete Order
@mongo_login_required
def order_delete(request, pk):
    order_collection = get_orders_collection()

    # 🔹 Fetch order
    order = order_collection.find_one({"_id": ObjectId(pk)})
    if not order:
        messages.error(request, "Order not found")
        return redirect("cnc_work_app:index")

    if request.method == "POST":
        confirm_title = request.POST.get("confirm_title", "").strip()
        actual_title = order.get("title", "").strip()

        # ❌ If title does NOT match → stop delete
        if confirm_title != actual_title:
            messages.error(request, "Entered title does not match. Order not deleted.")
            return redirect("cnc_work_app:order_delete", pk=pk)

        # 🔥 Delete image from Cloudinary
        image_url = order.get("image")
        if image_url:
            try:
                public_id = image_url.split("/")[-1].split(".")[0]
                destroy(f"orders/{public_id}")
            except Exception:
                pass  # use logger in production

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
@mongo_login_required
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

    # ---------------- COMPUTED STATUS NEW ----------------
    status_text, status_badge = get_order_display_status(
        order.get("order_status", [])
    )
    order["display_status"] = status_text
    order["status_badge"] = status_badge


    # ---------------- DESIGN FILES ----------------
    design_files = list(design_col.find({"order_id": pk}).sort("created_at", -1))
    for f in design_files:
        f["id"] = str(f["_id"])

    # ----------------- INVENTORY MASTER (Dropdown) -----------------
    inventory_items = list(inv_master_col.find({"is_active": True}))
    for i in inventory_items:
        i["id"] = str(i["_id"])  # 🔥 VERY IMPORTANT

    # ----------------- ORDER INVENTORY (TABLE) -----------------
    order_inventory = list(order_inv_col.find({"order_id": ObjectId(pk)}))
    for oi in order_inventory:
        oi["id"] = str(oi["_id"])  # ✅ THIS WAS MISSING

    # ---------------- MACHINE MASTER (Dropdown) ----------------
    machines_mast = list(machine_master_col.find({"is_active": True}))
    for m in machines_mast:
        m["id"] = str(m["_id"])  # ✅ for dropdown

    # ---------------- MACHINE WORK (Table + Delete/Edit) ----------------
    machines = list(machine_work_col.find({"order_id": pk}).sort("created_at", -1))

    total_hours = 0
    for m in machines:
        m["id"] = str(m["_id"])  # 🔥 MOST IMPORTANT LINE
        m["machine_date"] = m.get("date")  # safe mapping
        total_hours += float(m.get("working_hour", 0))

    # ---------------------- QUALITY CHECK  ----------------------
    quality_checks = list(qc_col.find({"order_id": pk}).sort("created_at", -1))
    for q in quality_checks: q["id"] = str(q["_id"])

    print(f"Quality checks: {quality_checks}")

    #  ---------------------- DISPATCH  ----------------------
    dispatches = list(dispatch_col.find({"order_id": ObjectId(pk)}).sort("created_at", -1))
    for d in dispatches: d["id"] = str(d["_id"])


    # ================= SALES USERS (DROPDOWN) =================
    users_col = users_collection()

    sales_users = list(users_col.find(
        {"roles": "SALES", "is_active": True},
        {"username": 1, "full_name": 1}
    ))

    permissions = get_user_permissions(request)

    context = {
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
        # Sales Person
        "sales_users": sales_users,
        # Permission
        "is_admin": permissions["override"],
        "can_sales": permissions["sales"],
        "can_designer" : permissions["designer"],
        "can_inventory": permissions["inventory"],
        "can_production": permissions["production"],
        "can_qc": permissions["qc"],
        "can_dispatch": permissions["dispatch"],
    }

    # ---------------- RENDER ----------------
    return render(request, "cnc_work_app/detail.html", context )


# Quality & Dispatch Session
@mongo_login_required
def add_quality_check(request, order_id):
    if request.method == "POST":
        qc_collection = get_quality_collection()
        orders_collection = get_orders_collection()

        # ---- INSERT QC RECORD ----
        qc_collection.insert_one({
            "order_id": order_id,
            "checked_by": request.POST.get("checked_by"),
            "status": request.POST.get("status"),
            "remarks": request.POST.get("remarks"),
            "checked_at": datetime.utcnow(),
        })

        now = datetime.utcnow()

        order = orders_collection.find_one({"_id": ObjectId(order_id)})

        updated_status = []
        stages_found = {
            "INVENTORY": False,
            "MACHINE": False,
            "DISPATCH": False
        }

        for s in order.get("order_status", []):
            if s["stage"] == "INVENTORY":
                s["status"] = "COMPLETE"
                s["updated_at"] = now
                stages_found["INVENTORY"] = True

            elif s["stage"] == "MACHINE":
                s["status"] = "COMPLETE"
                s["updated_at"] = now
                stages_found["MACHINE"] = True

            elif s["stage"] == "DISPATCH":
                s["status"] = "PENDING"
                s["updated_at"] = now
                stages_found["DISPATCH"] = True

            updated_status.append(s)

        # ---- ADD MISSING STAGES ----
        if not stages_found["INVENTORY"]:
            updated_status.append({
                "stage": "INVENTORY",
                "status": "COMPLETE",
                "updated_at": now
            })

        if not stages_found["MACHINE"]:
            updated_status.append({
                "stage": "MACHINE",
                "status": "COMPLETE",
                "updated_at": now
            })

        if not stages_found["DISPATCH"]:
            updated_status.append({
                "stage": "DISPATCH",
                "status": "PENDING",
                "updated_at": now
            })

        # ---- FINAL UPDATE ----
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "current_status": "Dispatch Pending",
                "order_status": updated_status
            }}
        )

    return redirect("cnc_work_app:detail", pk=order_id)


# Order Dispatches
@mongo_login_required
def add_dispatch(request, order_id):
    order_collection = get_orders_collection()
    dispatch_collection = get_dispatch_collection()

    # 🔹 Fetch order
    order = order_collection.find_one({"_id": ObjectId(order_id)})
    if not order: raise Http404("Order not found")

    # 🔒 Prevent double dispatch
    if order.get("current_status") == "Complete": raise Http404("Order already dispatched")

    if request.method == "POST":

        # ---- INSERT DISPATCH RECORD ----
        dispatch_collection.insert_one({
            "order_id": ObjectId(order_id),
            "vehicle_no": request.POST.get("vehicle_no"),
            "lr_no": request.POST.get("lr_no"),
            "dispatch_date": request.POST.get("dispatch_date"),
            "dispatched_by": request.POST.get("dispatched_by"),
            "remarks": request.POST.get("remarks"),
            "created_at": datetime.utcnow()
        })

        now = datetime.utcnow()

        # ---- UPDATE ORDER_STATUS ----
        updated_status = []
        dispatch_found = False

        for s in order.get("order_status", []):
            if s["stage"] == "DISPATCH":
                s["status"] = "COMPLETE"
                s["updated_at"] = now
                dispatch_found = True
            updated_status.append(s)

        if not dispatch_found:
            updated_status.append({
                "stage": "DISPATCH",
                "status": "COMPLETE",
                "updated_at": now
            })

        # ---- FINAL ORDER UPDATE ----
        order_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "current_status": "Complete",
                "dispatched_at": now,
                "order_status": updated_status
            }}
        )

    return redirect("cnc_work_app:detail", pk=order_id)


# Active Machines For Dropdown in Detail Page
def get_active_machines():
    col = get_machine_master_collection()
    machines = list(col.find({"is_active": True}))
    for m in machines:
        m["id"] = str(m["_id"])
    return machines


