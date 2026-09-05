"""
Payments Module - Manual Approval
Users send screenshot, admin verifies and approves manually
"""

import logging
import random
import string
from datetime import datetime, timedelta
from pymongo import MongoClient
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MONGO_URI = "mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLANS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLANS = {
    "core": {
        "display": "𝗖𝗼𝗿𝗲 🛠️",
        "days": 7,
        "credits": 13000,
        "price": 10
    },
    "elite": {
        "display": "𝗘𝗹𝗶𝘁𝗲 ⭐",
        "days": 15,
        "credits": 23000,
        "price": 15
    },
    "root": {
        "display": "𝗥𝗼𝗼𝘁 👑",
        "days": 30,
        "credits": 53000,
        "price": 30
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAYMENT NETWORKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIRECT_NETWORKS = {
    "trc20": {
        "name": "𝗨𝗦𝗗𝗧 (𝗧𝗥𝗖𝟮𝟬)",
        "currency": "USDT",
        "network": "TRC20",
        "address": "TJdQfLWo6mCSa2XnvjAV72eTK4qeWNDdRw",
        "emoji": "💎"
    },
    "binance": {
        "name": "𝗕𝗶𝗻𝗮𝗻𝗰𝗲 𝗣𝗮𝘆",
        "currency": "USDT",
        "network": "BINANCE",
        "address": "550157299",
        "emoji": "🟡"
    },
    "ltc": {
        "name": "𝗟𝗶𝘁𝗲𝗰𝗼𝗶𝗻",
        "currency": "LTC",
        "network": "LTC",
        "address": "ltc1qj2smwpp6252vxv8m6cc7dkftes3wjmshtl3xtvej457etdjd2nqypvjqn",
        "emoji": "⚡"
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_bot = None
user_sessions = {}
pending_payments = {}  # track_id -> {user_id, plan, network, address, amount, status}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _get_db():
    client = MongoClient(MONGO_URI)
    return client["MASTER_DATABASE"], client

def generate_receipt_id():
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"CARDX-{random_str}-CHK"

def set_bot(bot):
    global _bot
    _bot = bot

def get_bot():
    return _bot

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER SESSIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def set_user_session(user_id, plan):
    user_sessions[user_id] = {"plan": plan, "timestamp": time.time()}

def get_user_session(user_id):
    return user_sessions.get(user_id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KEYBOARDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_plan_selection_keyboard():
    kb = []
    for key, plan in PLANS.items():
        kb.append([InlineKeyboardButton(
            text=f"{plan['display']} - ${plan['price']} ({plan['days']} 𝗗𝗮𝘆𝘀)",
            callback_data=f"pay_plan_{key}"
        )])
    kb.append([InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="menu_pricing")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_network_selection_keyboard(user_id):
    kb = []
    for key, net in DIRECT_NETWORKS.items():
        kb.append([InlineKeyboardButton(
            text=f"{net['emoji']} {net['name']}",
            callback_data=f"pay_direct_{key}"
        )])
    kb.append([InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data=f"pay_back_plans_{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_paid_button_keyboard(track_id, user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ 𝗜 𝗛𝗮𝘃𝗲 𝗣𝗮𝗶𝗱", callback_data=f"pay_submit_{track_id}")],
        [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data=f"pay_back_plans_{user_id}")]
    ])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAYMENT CREATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def create_payment(user_id, plan, currency, network):
    track_id = f"PAY-{random.randint(100000, 999999)}"
    net_info = DIRECT_NETWORKS.get(network)
    if not net_info:
        return None
    
    pending_payments[track_id] = {
        "user_id": user_id,
        "plan": plan,
        "currency": currency,
        "network": network,
        "address": net_info["address"],
        "amount": PLANS[plan]["price"],
        "created_at": time.time(),
        "status": "pending"
    }
    
    return {
        "track_id": track_id,
        "address": net_info["address"],
        "amount": PLANS[plan]["price"],
        "currency": currency,
        "network": network,
        "plan": plan
    }

def format_payment_caption(payment_data, plan):
    pi = PLANS.get(plan, {})
    net_info = DIRECT_NETWORKS.get(payment_data["network"], {})
    return (
        f"💳 <b>𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗗𝗲𝘁𝗮𝗶𝗹𝘀</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>𝗣𝗹𝗮𝗻:</b> {pi.get('display', plan)}\n"
        f"<b>𝗔𝗺𝗼𝘂𝗻𝘁:</b> ${pi.get('price', 0)} {payment_data['currency']}\n"
        f"<b>𝗡𝗲𝘁𝘄𝗼𝗿𝗸:</b> {net_info.get('name', payment_data['network'])}\n"
        f"<b>𝗔𝗱𝗱𝗿𝗲𝘀𝘀:</b> <code>{payment_data['address']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>𝗦𝗲𝗻𝗱 𝗲𝘅𝗮𝗰𝘁 𝗮𝗺𝗼𝘂𝗻𝘁</b>\n"
        f"<i>Then click 'I Have Paid' and send screenshot to @npnbit4</i>"
    )

def register_payment(track_id, user_id, plan):
    if track_id in pending_payments:
        pending_payments[track_id]["user_id"] = user_id
        pending_payments[track_id]["plan"] = plan

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MANUAL APPROVAL - Admin only
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def activate_plan(user_id, plan):
    """ACTIVATE PLAN - ADMIN ONLY (called from /approve command)"""
    try:
        db, client = _get_db()
        users = db["USERSDB"]
        
        pi = PLANS.get(plan, {})
        days = pi.get("days", 7)
        credits = pi.get("credits", 13000)
        expiry_date = datetime.now() + timedelta(days=days)
        
        users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "is_premium": 1,
                    "premium_expiry": expiry_date.isoformat(),
                    "plan": pi.get("display", plan)
                },
                "$inc": {"credits": credits}
            },
            upsert=True
        )
        
        receipt_id = generate_receipt_id()
        receipts = db["receipts"]
        receipts.insert_one({
            "user_id": user_id,
            "receipt_id": receipt_id,
            "plan": pi.get("display", plan),
            "plan_name": pi.get("display", plan),
            "days": days,
            "credits": credits,
            "amount": pi.get("price", 0),
            "purchased_on": datetime.now().isoformat(),
            "expires_on": expiry_date.isoformat()
        })
        
        client.close()
        return receipt_id
    except Exception as e:
        logging.error(f"activate_plan error: {e}")
        return None

def get_pending_payment(track_id):
    return pending_payments.get(track_id)

def mark_payment_submitted(track_id):
    if track_id in pending_payments:
        pending_payments[track_id]["status"] = "submitted"
        return pending_payments[track_id]
    return None

def get_receipt_for_user(user_id, plan):
    try:
        db, client = _get_db()
        receipts = db["receipts"]
        receipt = receipts.find_one({"user_id": user_id, "plan": plan}, sort=[("purchased_on", -1)])
        client.close()
        return receipt
    except:
        return None

def _cleanup_payment(track_id, user_id):
    if track_id in pending_payments:
        del pending_payments[track_id]
    if user_id in user_sessions:
        del user_sessions[user_id]
