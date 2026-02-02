from django.urls import path
from lead_app.views import admin_views, sales_views



app_name = "lead_app"

urlpatterns = [

    # ADMIN
    path("admin/limits/", admin_views.sales_limit_list, name="sales_limits"),
    path("admin/set-limit/", admin_views.set_limit_view, name="set_limit"),
    path("admin/assign-lead/<str:lead_id>/<str:username>/",
         admin_views.assign_lead_view, name="assign_lead"),

    # SALES
    path("sales/leads/", sales_views.my_leads_view, name="my_leads"),
    path("sales/lead/<str:lead_id>/", sales_views.lead_detail_view, name="lead_detail"),
]
