from datetime import datetime
from bson import ObjectId
from utils.mongo import followups_col

def add_followup(lead_id, date, remark):
    followups_col().insert_one({
        "lead_id": ObjectId(lead_id),
        "followup_date": date,
        "remarks": remark,
        "created_at": datetime.now()
    })

def last_5_followups(lead_id):
    return list(
        followups_col()
        .find({"lead_id": ObjectId(lead_id)})
        .sort("created_at", -1)
        .limit(5)
    )
