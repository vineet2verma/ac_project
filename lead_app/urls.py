from django.urls import path
from lead_app.admin_views import (
    sales_limit_list, set_limit_view, assign_lead_view
)
from lead_app.sales_views import (
    my_leads_view, lead_detail_view
)

app_name = "lead_app"

urlpatterns = [

    # ADMIN
    path("admin/limits/", sales_limit_list, name="sales_limits"),
    path("admin/set-limit/", set_limit_view, name="set_limit"),
    path("admin/assign-lead/<str:lead_id>/<str:username>/",assign_lead_view, name="assign_lead"),
    # SALES
    path("sales/leads/", my_leads_view, name="my_leads"),
    path("sales/lead/<str:lead_id>/", lead_detail_view, name="lead_detail"),
]
