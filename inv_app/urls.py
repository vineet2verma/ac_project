from django.urls import path
from .views import (inventory_bulk_upload, inventory_master_view, inventory_master_delete,
                    inventory_template_download, category_master, category_delete)

app_name = 'inv_app'

urlpatterns = [
    # Inventory
    path("inventory/master/", inventory_master_view, name="inventory_master"),
    path("inventory/bulk-upload/", inventory_bulk_upload, name="inventory_bulk_upload"),
    path("inventory/<str:pk>/delete/", inventory_master_delete, name="inventory_delete"),
    path("inventory/template/download/",inventory_template_download,name="inventory_template_download"),

    # Category Master
    path("inventory/category/", category_master, name="category_master"),
    path("inventory/category/<str:pk>/delete/", category_delete, name="category_delete"),
]
