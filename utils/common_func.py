from .mongo import *



def get_active_sales_users():
    return list(
        users_collection().find(
            {"roles": "SALES","is_active": True},
            {"_id": 0, "username": 1, "full_name": 1, "email": 1, "roles": 1}
        ).sort("username", 1)
    )