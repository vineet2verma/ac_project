from django.urls import path
from . import views

app_name = "order_costing_app"

urlpatterns = [
    # ================= ORDER COSTING =================
    path("order/<str:order_id>/costing/", views.order_costing_view, name="order_costing"),
    # Rate Config
    path("rate-config/", views.rate_config_view, name="rate_config"),


]
