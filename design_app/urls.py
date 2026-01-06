from django.urls import path
from . import views

app_name = 'design_app'

urlpatterns = [
    # Design
    path('order/<str:pk>/design/add/', views.add_design_file, name='add_design_file'),
    path("design-file/<str:design_id>/<str:action>/", views.design_action, name="design_action"),
    path("order/<str:order_id>/design/<str:design_id>/delete/", views.design_delete, name="design_delete"),
]
