
from pymongo import MongoClient
<<<<<<< HEAD

from django.conf import settings
=======
from django.conf import settings

>>>>>>> 48cccbf (Initial commit on ac_project)
MONGO_URI = 'mongodb+srv://vineet2verma_db_user:3GyLmAJkpY083hwR@erp-cluster.9ayivjz.mongodb.net/?appName=erp-cluster'


def get_db():
    client = MongoClient(MONGO_URI)
    return client['cnc_db']

def get_orders_collection():
    db = get_db()
    return db['order']





