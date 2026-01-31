from django.urls import path
from . import views

app_name = "core_app"


urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("error-page/",views.error_page,name="error_page"),
    path("sales-person/<str:username>/",views.sales_person_detail,name="sales_person_detail"),
    # EXCEL EXPORT PDF
    path("sales-person/<str:username>/export/pdf/",views.export_orders_pdf,name="export_orders_pdf"),
    # ✅ EXCEL EXPORT (ADD THIS)
    path("sales-person/<str:username>/export/excel/",views.export_orders_excel,name="export_orders_excel"),


]
