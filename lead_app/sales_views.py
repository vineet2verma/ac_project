from django.shortcuts import render, redirect
from bson import ObjectId
from lead_app.services.lead_query_service import my_leads, update_status
from lead_app.services.followup_service import add_followup, last_5_followups
from utils.mongo import leads_col

def my_leads_view(request):
    leads = my_leads(request.user.username)
    return render(request, "sales/my_leads.html", {"leads": leads})

def lead_detail_view(request, lead_id):
    lead = leads_col().find_one({"_id": ObjectId(lead_id)})
    followups = last_5_followups(lead_id)

    if request.method == "POST":
        if "status" in request.POST:
            update_status(lead_id, request.POST["status"])
        if "remark" in request.POST:
            add_followup(
                lead_id,
                request.POST["followup_date"],
                request.POST["remark"]
            )
        return redirect("lead_app:lead_detail", lead_id=lead_id)

    return render(request, "sales/lead_detail.html", {
        "lead": lead,
        "followups": followups
    })
