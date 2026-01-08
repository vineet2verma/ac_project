from django.urls import path
from . import views

app_name = 'machine_app'

urlpatterns = [
    # Machine Master
    path("master/",views.machine_master_view,name="machine_master_view"),
    path("master/add/",views.machine_master_add,name="machine_master_add"),
    path("master/toggle/<str:pk>/",views.machine_master_toggle,name="machine_master_toggle"),

    # ================= ORDER → MACHINE WORK =================
    path("order/<str:order_id>/machine/add/",views.add_machine_work,name="add_machine_work"),
    # Start machine (🔥 consumes inventory + design)
    path("order/<str:order_id>/machine/start/<str:work_id>/",views.machine_work_start,name="machine_work_start"),
    # Complete machine work
    path("order/<str:order_id>/machine/complete/<str:work_id>/",views.machine_work_complete,name="machine_work_complete"),
    # Delete machine work (ONLY if PENDING)
    path("order/<str:order_id>/machine/delete/<str:work_id>/",views.machine_delete,name="machine_delete"),


]
