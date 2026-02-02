import pandas as pd
from datetime import datetime
from utils.mongo import leads_col

def upload_leads_excel(file):
    df = pd.read_excel(file)

    for _, row in df.iterrows():
        if not row.get("Phone"):
            continue

        leads_col().insert_one({
            "name": row["Name"],
            "phone": str(row["Phone"]),
            "email": row.get("Email", ""),
            "source": row.get("Source", ""),
            "assigned_to": None,
            "status": "New",
            "created_at": datetime.now()
        })
