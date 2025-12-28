

from django.urls import path
from .views import add_orders

urlpatterns = [
    path('add-order/', add_orders ),
]
