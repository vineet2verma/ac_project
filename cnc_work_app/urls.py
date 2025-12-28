from django.urls import path
from . import views

app_name = 'cnc_work_app'

urlpatterns = [
    path('', views.cnc_order_list, name='index'),       # List view
    path('cnc_work_app/', views.cnc_order_list, name='index'),       # List view
    path('cnc_work_app/order/', views.add_order, name='add_order'),  # Form POST
    path('cnc_work_app/add/', views.add_image, name='add_image'),    # Form POST

    path("order/<str:pk>/", views.order_detail, name="detail"),  # order detail
    path('order/<str:pk>/edit/', views.order_edit, name='edit_order'),
    path("order/<str:pk>/delete/", views.order_delete, name="order_delete"), #Order Delete

    # Design
    path("design-file/<str:pk>/<str:action>/", views.design_file_action, name="design_file_action"),

    path('order/<str:pk>/design/add/', views.add_design_file, name='add_design_file'),
    path('order/<str:pk>/inventory/add/', views.add_inventory, name='add_inventory'),
    # path('cnc_work_app/detail/', views.view_detail, name='detail'),  # Details

    # Design Action
    path( "design-file/<int:pk>/<str:action>/", views.design_file_action, name="design_file_action"),
    
    # Machine Details
    path('machine/add/<int:order_id>/', views.machine_add_update, name='machine_add_update'),
    path('order/<int:order_id>/machine/<int:pk>/delete/', views.machine_delete, name='machine_delete'),


    # Machine Master
    path("machines_mast/", views.machine_mast_list, name="machine_list"),



]