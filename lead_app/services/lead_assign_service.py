
from bson import ObjectId
from utils.mongo import *

def assign_lead(lead_id, sales_user):
    limit = limits_col().find_one({"sales_user": sales_user})

    if not limit:
        return False, "Limit not set"

    balance = limit["total_limit"] - limit["assigned_count"]
    if balance <= 0:
        return False, "Limit exceeded"

    leads_col().update_one(
        {"_id": ObjectId(lead_id)},
        {"$set": {"assigned_to": sales_user}}
    )

    limits_col().update_one(
        {"sales_user": sales_user},
        {"$inc": {"assigned_count": 1}}
    )

    return True, "Lead assigned"


def set_limit(username, limit):
    from utils.mongo import limits_col
    limits_col().update_one(
        {"sales_user": username},
        {"$set": {"total_limit": limit, "assigned_count": 0}},
        upsert=True
    )


def get_sales_limits():
    limits = list(limits_col().find())
    for l in limits:
        l["balance"] = l["total_limit"] - l["assigned_count"]
    return limits
