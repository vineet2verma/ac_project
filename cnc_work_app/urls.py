from django.urls import path
from . import views

app_name = 'cnc_work_app'

urlpatterns = [
    path('cnc_work_app/', views.cnc_order_list, name='index'),       # List view
    path('cnc_work_app/order/', views.add_order, name='add_order'),  # Form POST
    path('cnc_work_app/add/', views.add_image, name='add_image'),    # Form POST
    path("order/<int:pk>/delete/", views.order_delete, name="order_delete"), #Order Delete

    path("order/<int:pk>/", views.order_detail, name="detail"),

    # Design
    path("design-file/<int:pk>/<str:action>/",views.design_file_action,name="design_file_action"),

    path('order/<int:pk>/edit/', views.order_edit, name='edit_order'),
    path('order/<int:pk>/design/add/', views.add_design_file, name='add_design_file'),
    path('order/<int:pk>/inventory/add/', views.add_inventory, name='add_inventory'),
    # path('cnc_work_app/detail/', views.view_detail, name='detail'),  # Details

    # Design Action
    path( "design-file/<int:pk>/<str:action>/", views.design_file_action, name="design_file_action" ),
    
    # Machine Details
    path('machine/add/<int:order_id>/', views.machine_add_update, name='machine_add_update'),
    path('order/<int:order_id>/machine/<int:pk>/delete/',views.machine_delete,name='machine_delete'),


    # Machine Master
    path("machines_mast/", views.machine_mast_list, name="machine_list"),



]