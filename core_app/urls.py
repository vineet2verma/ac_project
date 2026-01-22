from django.urls import path
from . import views

app_name = "core_app"


urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("error-page/",views.error_page,name="error_page"),

]
