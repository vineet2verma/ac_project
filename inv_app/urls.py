
from django.urls import path
from . import views

app_name = 'inv_app'

urlpatterns = [
    # Inventory
    path("inventory/master/", views.inventory_master_view, name="inventory_master"),
    path("inventory/<str:pk>/delete/", views.inventory_master_delete, name="inventory_delete"),

    # Category Master
    path("inventory/category/", views.category_master, name="category_master"),
    path("inventory/category/<str:pk>/delete/", views.category_delete, name="category_delete"),
]
