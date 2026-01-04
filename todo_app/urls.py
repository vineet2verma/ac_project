from django.urls import path
from .views import todo_list, todo_add, request_done, approve_done, todo_edit, todo_delete, todo_dashboard

app_name = "todo_app"

urlpatterns = [
    path("todo/", todo_list, name="list"),
    path("add/", todo_add, name="add"),
    path("request-done/<str:todo_id>/", request_done, name="request_done"),
    path("approve-done/<str:todo_id>/", approve_done, name="approve_done"),
    path("edit/<str:todo_id>/", todo_edit, name="edit"),
    path("delete/<str:todo_id>/", todo_delete, name="delete"),
    path("todo/dashboard/", todo_dashboard, name="dashboard"),
]
