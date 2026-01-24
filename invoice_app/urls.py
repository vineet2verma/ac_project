from django.urls import path
from . import views

app_name = 'invoice_app'

urlpatterns = [

    # Quotation List
    path("quotations/", views.quotation_list, name="quotation_list"),
    # Quotation Create
    path("quotation/create/", views.quotation_create, name="quotation_create"),
    # Quotation View
    path("quotation/view/<str:qid>/", views.quotation_view, name="quotation_view"),
    # Quotation Delete
    path("quotation/delete/<str:qid>/",views.quotation_delete,name="quotation_delete"),

]


