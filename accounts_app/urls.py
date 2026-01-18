from django.urls import path
from . import views

app_name = "accounts_app"

urlpatterns = [
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("role-not-defined/", views.role_not_defined, name="role_not_defined"),
    # User
    path("users/", views.user_master, name="user_master"),
    # Reset Password
    path("users/<str:user_id>/reset-password/",views.admin_reset_password,name="admin_reset_password"),
    path("admin-reset-password/<str:user_id>/", views.admin_reset_password,name="admin_reset_password"),


]
