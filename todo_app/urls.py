from django.urls import path
from . import views

app_name = "todo_app"

urlpatterns = [
    # Old
    path("todo/", views.todo_list, name="list"),
    path("add/", views.todo_add, name="add"),
    path("request-done/<str:todo_id>/", views.request_done, name="request_done"),
    path("approve-done/<str:todo_id>/", views.approve_done, name="approve_done"),
    path("edit/<str:todo_id>/", views.todo_edit, name="edit"),
    path("delete/<str:todo_id>/", views.todo_delete, name="delete"),
    path("todo/dashboard/", views.todo_dashboard, name="dashboard"),
]
