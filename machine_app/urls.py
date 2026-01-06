from django.urls import path
from . import views

app_name = 'machine_app'

urlpatterns = [
    # Machine Master
    path("machine-master/", views.machine_master_view, name="machine_master_view"),
    path("machine-master/add/", views.machine_master_add, name="machine_master_add"),
    path("machine-master/toggle/<str:pk>/", views.machine_master_toggle, name="machine_master_toggle"),
    # Machine Working : Order
    # Machine Work Detail
    path("order/<str:order_id>/machine/add/", views.add_machine_work, name="add_machine_work"),
    path("order/<str:order_id>/machine/<str:machine_work_id>/edit/", views.machine_edit, name="machine_edit"),
    path("order/<str:order_id>/machine/<str:machine_work_id>/delete/", views.machine_delete, name="machine_delete"),

]
