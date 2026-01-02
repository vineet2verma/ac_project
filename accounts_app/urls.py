from django.urls import path
from .views import login_view, logout_view, signup_view, forgot_password, reset_password
from .views import user_master, update_user

app_name = "accounts_app"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("signup/", signup_view, name="signup"),
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("users/reset-password/<str:user_id>/", reset_password, name="reset_password"),
    # User
    path("users/", user_master, name="user_master"),
    path("users/update/<str:user_id>/", update_user, name="update_user"),

]
