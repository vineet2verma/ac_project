from django.shortcuts import render, redirect
from django.contrib import messages
from lead_app.services.lead_assign_service import (
    set_limit, assign_lead, get_sales_limits
)
from utils.mongo import leads_col

def sales_limit_list(request):
    """
    Custom Admin Dashboard (Mongo-based)
    """
    limits = get_sales_limits()
    unassigned_leads = list(
        leads_col().find({"assigned_to": None})
    )

    return render(request, "admin/sales_limits.html", {
        "limits": limits,
        "leads": unassigned_leads
    })

def set_limit_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        limit = int(request.POST["limit"])

        set_limit(username, limit)
        messages.success(request, "Lead limit saved")

    return redirect("lead_app:sales_limits")

def assign_lead_view(request, lead_id, username):
    success, msg = assign_lead(lead_id, username)
    messages.success(request, msg) if success else messages.error(request, msg)
    return redirect("lead_app:sales_limits")