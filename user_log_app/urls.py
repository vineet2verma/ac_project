from django.urls import path
from .views import login_activity_view

app_name = "user_log_app"

urlpatterns = [
    path("login-activity/", login_activity_view, name="login_activity"),
]
