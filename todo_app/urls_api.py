from django.urls import path
from .views_api import *

urlpatterns = [
    path("api/todo/", api_todo_list),
    path("api/todo/add/", api_todo_add),
    path("api/todo/update/<str:todo_id>/", api_todo_update),
    path("api/todo/delete/<str:todo_id>/", api_todo_delete),
    path("api/todo/request-done/<str:todo_id>/", api_request_done),
    path("api/todo/approve-done/<str:todo_id>/", api_approve_done),
]
