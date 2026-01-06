from django.urls import path
from . import views
# from .views import (inventory_bulk_upload, inventory_master_view, inventory_master_delete,
#                     inventory_template_download,inventory_ledger_view,delete_stock_in,
#                     category_master, category_delete,add_order_inventory,delete_order_inventory
#
#                     )

app_name = 'inv_app'

urlpatterns = [
    # Inventory
    path("inventory/master/", views.inventory_master_view, name="inventory_master"),
    path("inventory/bulk-upload/", views.inventory_bulk_upload, name="inventory_bulk_upload"),
    path("inventory/<str:pk>/delete/", views.inventory_master_delete, name="inventory_delete"),
    path("inventory/template/download/",views.inventory_template_download,name="inventory_template_download"),
    # path("inventory/stock-in/",inventory_stock_in,name="inventory_stock_in"),
    path("inventory/ledger/",views.inventory_ledger_view,name="inventory_ledger"),
    path("inventory/ledger/delete-stock-in/<str:ledger_id>/",views.delete_stock_in,name="delete_stock_in"),

    # Inventory
    path("order/<str:order_id>/inventory/add/", views.add_order_inventory, name="order_inventory_add"),
    path("order/<str:order_id>/inventory/delete/<str:inv_id>/", views.delete_order_inventory, name="delete_inventory"),
    path("order/<str:order_id>/check/", views.inventory_check, name="check"),
    path("reserve/<str:inv_id>/", views.inventory_reserve, name="reserve"),
    path("pr/create/<str:inv_id>/", views.create_purchase_requisition, name="pr_create"),
    path("pr/<str:order_id>/", views.pr_list, name="pr_list"),   # ✅ ADD THIS
    path("pr/receive/<str:pr_id>/", views.material_received, name="pr_receive"),

    # Category Master
    path("inventory/category/", views.category_master, name="category_master"),
    path("inventory/category/<str:pk>/delete/", views.category_delete, name="category_delete"),
]
