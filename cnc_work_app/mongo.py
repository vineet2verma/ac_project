
from pymongo import MongoClient
from django.conf import settings
import os

MONGO_URI = 'mongodb+srv://vineet2verma_db_user:3GyLmAJkpY083hwR@erp-cluster.9ayivjz.mongodb.net/?appName=erp-cluster'

def get_db():
    client = MongoClient(MONGO_URI)
    return client['cnc_db']

def get_mongo_client():
    return MongoClient(os.getenv("MONGO_URI"))

def get_orders_collection():
    client = get_mongo_client()
    db = client["erp_db"]
    return db["orders"]

# ✅ ADD THIS
def get_quality_collection():
    client = get_mongo_client()
    db = client["erp_db"]
    return db["quality_checks"]









