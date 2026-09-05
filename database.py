"""
MongoDB Database Layer
Using MASTER_DATABASE.USERSDB
"""

import logging
import time
from datetime import datetime
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONNECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
client = MongoClient(MONGO_URI)
db = client["MASTER_DATABASE"]
USERS = db["USERSDB"]
RECEIPTS = db["receipts"]
CODES = db["GCDB"]
CONF = db["CONF_DATABASE"]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INDEXES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    USERS.create_index("user_id", unique=True)
    CODES.create_index("code", unique=True)
    print("[DB] MongoDB indexes created")
except Exception as e:
    print(f"[DB] Index error: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_user(user_id: int):
    try:
        return USERS.find_one({"user_id": user_id})
    except Exception as e:
        logging.error(f"get_user error: {e}")
        return None

def get_user_credits(user_id: int) -> int:
    try:
        user = USERS.find_one({"user_id": user_id}, {"credits": 1})
        return user.get("credits", 0) if user else 0
    except Exception as e:
        logging.error(f"get_user_credits error: {e}")
        return 0

def update_credits(user_id: int, new_credits: int):
    try:
        USERS.update_one(
            {"user_id": user_id},
            {"$set": {"credits": new_credits}}
        )
        return True
    except Exception as e:
        logging.error(f"update_credits error: {e}")
        return False

def create_user(user_id: int, username: str = None):
    try:
        USERS.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "username": username or "Unknown",
                "first_name": "User",
                "credits": 150,
                "is_premium": 0,
                "premium_expiry": None,
                "joined_at": datetime.now().isoformat(),
                "cc_checked": 0,
                "cc_charged": 0
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logging.error(f"create_user error: {e}")
        return False

def get_premium_status(user_id: int):
    try:
        user = USERS.find_one({"user_id": user_id}, {"is_premium": 1, "premium_expiry": 1, "plan": 1})
        if not user:
            return False, None
        is_premium = user.get("is_premium", 0) == 1
        expiry = user.get("premium_expiry")
        plan = user.get("plan", "Trial")
        if is_premium and expiry:
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            if datetime.now() > expiry:
                USERS.update_one(
                    {"user_id": user_id},
                    {"$set": {"is_premium": 0, "premium_expiry": None, "credits": 150}}
                )
                return False, None
        return is_premium, expiry
    except Exception as e:
        logging.error(f"get_premium_status error: {e}")
        return False, None

def is_gate_enabled(gate: str) -> bool:
    try:
        doc = CONF.find_one({"gate": gate})
        if doc:
            return doc.get("is_enabled", True)
        return True
    except Exception as e:
        logging.error(f"is_gate_enabled error: {e}")
        return True

def set_gate_status(gate: str, enabled: bool):
    try:
        CONF.update_one(
            {"gate": gate},
            {"$set": {"is_enabled": enabled, "updated_at": datetime.now().isoformat()}},
            upsert=True
        )
        return True
    except Exception as e:
        logging.error(f"set_gate_status error: {e}")
        return False

print("[DB] MongoDB CONNECTED SUCCESSFULLY ✅")
