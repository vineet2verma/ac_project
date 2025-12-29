
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))

MONGO_URI = os.environ.get("MONGO_URI")

# ✅ SINGLE CLIENT (IMPORTANT)
_client = MongoClient(MONGO_URI)
_db = _client["cnc_db"]

def get_orders_collection():
    return _db["order"]

def get_quality_collection():
    return _db["quality_checks"]

def get_dispatch_collection():
    return _db["dispatches"]

