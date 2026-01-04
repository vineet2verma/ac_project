
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

# User
def users_collection():
    return _db["users"]

# Master
def get_inventory_master_collection():
    return _db["inventory_masters"]

def get_inventory_ledger_collection():
    return _db["inventory_ledger"]

def category_collection():
    return _db["categories_masters"]

def get_machine_master_collection():
    return _db["machine_master"]

# Master End
# Collection
# Order Collection
def get_orders_collection():
    return _db["order"]
# order_inventory
def get_order_inventory_collection():
    return _db["order_inventory"]

# Order Design
def get_design_files_collection():
    return _db["design_files"]
# Order Machine
def get_machine_work_collection():
    return _db["machine_work"]
# Order QC
def get_quality_collection():
    return _db["quality_checks"]
# Order Dispatch
def get_dispatch_collection():
    return _db["dispatches"]

# To Do's
def todo_collection():
    return _db["todos"]