from django.urls import path
from . import views

app_name = 'invoice_app'

urlpatterns = [
    path('quotation-list/', views.invoice_list, name='invoice_list'),
    path('create/', views.create_invoice, name='create_invoice'),

]


