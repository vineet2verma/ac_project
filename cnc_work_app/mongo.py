
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

# Master
def get_machine_master_collection():
    return _db["machine_master"]

def get_inventory_master_collection():
    return _db["inventory_masters"]

def category_collection():
    return _db["inventory_categories"]

# db working
def get_orders_collection():
    return _db["order"]

def get_order_inventory_collection():
    return _db["order_inventory"]

def get_design_files_collection():
    return _db["design_files"]

def get_machine_work_collection():
    return _db["machine_work"]

def get_inventory_collection():
    return _db["inventory"]

def get_quality_collection():
    return _db["quality_checks"]

def get_dispatch_collection():
    return _db["dispatches"]


