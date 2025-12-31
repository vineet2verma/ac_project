from django.urls import path
from . import views

app_name = 'inv_app'

urlpatterns = [
    # Category Master
    path("inventory/category/", views.category_master, name="category_master"),
    path("inventory/category/<str:pk>/delete/", views.category_delete, name="category_delete"),

    # Inventory
    path("inventory/master/", views.inventory_master, name="inventory_master"),
    path("inventory/<str:pk>/delete/", views.inventory_delete, name="inventory_delete"),



]
