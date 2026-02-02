from bson import ObjectId
from utils.mongo import leads_col, limits_col


def set_limit(username, limit):
    limits_col().update_one(
        {"sales_user": username},
        {"$set": {"total_limit": limit, "assigned_count": 0}},
        upsert=True
    )

def assign_lead(lead_id, sales_user):
    limit = limits_col().find_one({"sales_user": sales_user})

    if not limit:
        return False, "Limit not set"

    if limit["assigned_count"] >= limit["total_limit"]:
        return False, "Limit exceeded"

    leads_col().update_one(
        {"_id": ObjectId(lead_id)},
        {"$set": {"assigned_to": sales_user}}
    )

    limits_col().update_one(
        {"sales_user": sales_user},
        {"$inc": {"assigned_count": 1}}
    )

    return True, "Lead assigned successfully"

def get_sales_limits():
    limits = list(limits_col().find())
    for l in limits:
        l["balance"] = l["total_limit"] - l["assigned_count"]
    return limits
