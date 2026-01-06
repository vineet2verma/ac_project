from django.urls import path
from .views import (inventory_bulk_upload, inventory_master_view, inventory_master_delete,
                    inventory_template_download,inventory_ledger_view,delete_stock_in,
                    category_master, category_delete,add_order_inventory,delete_order_inventory

                    )

app_name = 'inv_app'

urlpatterns = [
    # Inventory
    path("inventory/master/", inventory_master_view, name="inventory_master"),
    path("inventory/bulk-upload/", inventory_bulk_upload, name="inventory_bulk_upload"),
    path("inventory/<str:pk>/delete/", inventory_master_delete, name="inventory_delete"),
    path("inventory/template/download/",inventory_template_download,name="inventory_template_download"),
    # path("inventory/stock-in/",inventory_stock_in,name="inventory_stock_in"),
    path("inventory/ledger/",inventory_ledger_view,name="inventory_ledger"),
    path("inventory/ledger/delete-stock-in/<str:ledger_id>/",delete_stock_in,name="delete_stock_in"),

    # Inventory
    path("order/<str:order_id>/inventory/add/", add_order_inventory, name="order_inventory_add"),
    path("order/<str:order_id>/inventory/delete/<str:inv_id>/", delete_order_inventory, name="delete_inventory"),

    # Category Master
    path("inventory/category/", category_master, name="category_master"),
    path("inventory/category/<str:pk>/delete/", category_delete, name="category_delete"),
]
