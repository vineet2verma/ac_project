from utils.mongo import leads_col
from bson import ObjectId


def my_leads(username):
    return list(leads_col().find({"assigned_to": username}))

def update_status(lead_id, status):
    leads_col().update_one(
        {"_id": ObjectId(lead_id)},
        {"$set": {"status": status}}
    )

