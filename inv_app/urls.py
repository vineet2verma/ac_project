from django.urls import path
from . import views

app_name = 'inv_app'

urlpatterns = [
    # Inventory Master
    path("inventory/master/", views.inventory_master_view, name="inventory_master"),
    # Inventory Master delete
    path("master/delete/<str:pk>/",views.inventory_master_delete,name="inventory_master_delete"),
    # path("inventory/<str:pk>/delete/", views.inventory_master_delete, name="inventory_delete"),
    # Bulk Upload
    path("inventory/bulk-upload/", views.inventory_bulk_upload, name="inventory_bulk_upload"),
    # Templates
    path("inventory/template/download/",views.inventory_template_download,name="inventory_template_download"),
    # Ledger
    path("inventory/ledger/",views.inventory_ledger_view,name="inventory_ledger"),
    # Inventory Check
    path("check/<str:order_id>/",views.inventory_check,name="check"),
    # Reserve
    path("reserve/<str:inv_id>/",views.inventory_reserve,name="inventory_reserve"),
    # Create PR
    path("pr/create/<str:inv_id>/",views.create_purchase_requisition,name="create_pr"),
    # PR List
    path("pr/<str:order_id>/",views.pr_list,name="pr_list"),
    # Material Received
    path("pr/receive/<str:pr_id>/",views.material_received,name="material_received"),
    #
    path(
        "pr/cancel/<str:pr_id>/",views.cancel_pr,name="cancel_pr"),


    path("inventory/ledger/delete-stock-in/<str:ledger_id>/",views.delete_stock_in,name="delete_stock_in"),

    # Order Add Inventory
    path("order/<str:order_id>/inventory/add/", views.add_order_inventory, name="order_inventory_add"),
    # Order Delete From Order
    path("order/<str:order_id>/inventory/delete/<str:inv_id>/", views.delete_order_inventory, name="delete_inventory"),

    # Category Master
    path("inventory/category/", views.category_master, name="category_master"),
    # Category Master Delete
    path("inventory/category/<str:pk>/delete/", views.category_delete, name="category_delete"),
]
