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


    # Quality Check
    path("order/<str:order_id>/qc/", views.add_quality_check, name="quality_check"),

    # Dispatch
    path("order/<str:order_id>/dispatch/", views.add_dispatch, name="dispatch_add"),

]
