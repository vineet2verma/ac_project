from django.urls import path
from . import views

app_name = 'cnc_work_app'

urlpatterns = [
    path('cnc_work_app/', views.cnc_order_list, name='index'),  # List view
    path('cnc_work_app/order/', views.add_order, name='add_order'),  # Form POST
    path("order/<str:pk>/delete/", views.order_delete, name="order_delete"),  # Order Delete
    path('order/<str:pk>/edit/', views.order_edit, name='edit_order'),
    # Detail
    path("order/<str:pk>/", views.order_detail, name="detail"),  # order detail

    # Design
    path('order/<str:pk>/design/add/', views.add_design_file, name='add_design_file'),
    path("design-file/<str:design_id>/<str:action>/", views.design_action, name="design_action"),
    path("order/<str:order_id>/design/<str:design_id>/delete/", views.design_delete, name="design_delete"),

    # Inventory
    path("order/<str:order_id>/inventory/add/", views.add_order_inventory, name="order_inventory_add"),
    path("order/<str:order_id>/inventory/delete/<str:inv_id>/",views.delete_order_inventory,name="delete_inventory"),

    # Machine Work Detail
    path("order/<str:order_id>/machine/add/", views.add_machine_work, name="add_machine_work"),
    path("order/<str:order_id>/machine/<str:machine_work_id>/edit/", views.machine_edit, name="machine_edit"),
    path("order/<str:order_id>/machine/<str:machine_work_id>/delete/", views.machine_delete, name="machine_delete"),

    # Machine Master
    path("machine-master/", views.machine_master, name="machine_master"),
    path("machine-master/add/", views.machine_master_add, name="machine_master_add"),
    path("machine-master/toggle/<str:pk>/", views.machine_master_toggle, name="machine_master_toggle"),

    # Quality Check
    path("order/<str:order_id>/qc/", views.add_quality_check, name="quality_check"),

    # Dispatch
    path("order/<str:order_id>/dispatch/", views.add_dispatch, name="dispatch_add"),

]
