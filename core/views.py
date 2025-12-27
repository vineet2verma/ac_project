from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .mongo import get_orders_collection
from django.utils import timezone



# Create your views here.
def add_orders(request):
    order = {
        'order_id': 'cnc-001',
        'date': timezone.now(),
        'customer_name': 'John Doe',
        'items': [
            {'item_name': 'Widget A', 'quantity': 2, 'price': 19.99},
            {'item_name': 'Widget B', 'quantity': 1, 'price': 29.99}
        ],
        'total_amount': 69.97,
        'sales_person': 'Jane Smith',
        'img_url': 'https://example.com/images/order123.jpg'
    }

    orders_collection = get_orders_collection()
    result = orders_collection.insert_one(order)

    return JsonResponse({'message': 'Order added successfully', 'order_id': str(result.inserted_id)})


    
