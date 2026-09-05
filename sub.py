import asyncio
import random
import string
import logging
import io
from datetime import datetime, timedelta

from aiogram import types, F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from database import get_user, get_user_credits, update_credits, create_user

router = Router()

ADMIN_ID = 6152006521
LOG_CHANNEL_ID = -1004408574006
DEV_USERNAME = "npnbit4"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_receipt_id():
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"CARDX-{random_str}-CHK"

def mask_receipt_id(receipt_id):
    parts = receipt_id.split('-')
    if len(parts) == 3:
        middle = parts[1]
        if len(middle) >= 2:
            masked_middle = middle[:2] + "XX" + middle[4:]
            return f"{parts[0]}-{masked_middle}-{parts[2]}"
    return receipt_id

def get_premium_status(user_id):
    """Get premium status from MongoDB"""
    try:
        user = get_user(user_id)
        if not user:
            return False, None
        is_premium = user.get("is_premium", 0) == 1
        expiry = user.get("premium_expiry")
        if is_premium and expiry:
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            if datetime.now() > expiry:
                update_credits(user_id, 150)
                return False, None
        return is_premium, expiry
    except Exception as e:
        logging.error(f"get_premium_status error: {e}")
        return False, None

def _resolve_user_id_sync(target_input):
    try:
        if target_input.isdigit():
            user = get_user(int(target_input))
            return user.get("user_id") if user else None
        else:
            username = target_input.lstrip('@')
            # Search by username (simple)
            from pymongo import MongoClient
            client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
            db = client["MASTER_DATABASE"]
            users = db["USERSDB"]
            user = users.find_one({"username": username})
            client.close()
            return user.get("user_id") if user else None
    except Exception as e:
        logging.error(f"_resolve_user_id_sync error: {e}")
        return None

def is_user_banned(user_id):
    try:
        user = get_user(user_id)
        return user.get("banned", False) if user else False
    except:
        return False

    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
        db = client["MASTER_DATABASE"]
        conf = db["CONF_DATABASE"]
        doc = conf.find_one({"gate": gate})
        client.close()
        if doc:
            return doc.get("is_enabled", True)
        return True
    except:
        return True

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /buy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_BUY_TEXT = (
    f'<b>𝗔𝗰𝗰𝗲𝘀𝘀 ➛ 𝗖𝗢𝗥𝗘</b> <tg-emoji emoji-id="5379869575338812919">💎</tg-emoji>\n'
    f'<b>𝗦𝗽𝗮𝗻 ➛</b> [𝟳 𝗗𝗔𝗬𝗦]\n'
    f'<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛</b> 𝟭𝟯,𝟬𝟬𝟬\n'
    f'<b>𝗣𝗿𝗶𝗰𝗲 ➛</b> 𝟭𝟬$\n'
    f'━━━━━━━━━━━━━━━━\n'
    f'<b>𝗔𝗰𝗰𝗲𝘀𝘀 ➛ 𝗘𝗟𝗜𝗧𝗘</b> <tg-emoji emoji-id="5836898273666798437">💎</tg-emoji>\n'
    f'<b>𝗦𝗽𝗮𝗻 ➛</b> [𝟭𝟱 𝗗𝗔𝗬𝗦]\n'
    f'<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛</b> 𝟮𝟯,𝟬𝟬𝟬\n'
    f'<b>𝗣𝗿𝗶𝗰𝗲 ➛</b> 𝟭𝟱$\n'
    f'━━━━━━━━━━━━━━━━\n'
    f'<b>𝗔𝗰𝗰𝗲𝘀𝘀 ➛ 𝗥𝗢𝗢𝗧</b> <tg-emoji emoji-id="4956420911310832630">💎</tg-emoji>\n'
    f'<b>𝗦𝗽𝗮𝗻 ➛</b> [𝟯𝟬 𝗗𝗔𝗬𝗦]\n'
    f'<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛</b> 𝟱𝟯,𝟬𝟬𝟬\n'
    f'<b>𝗣𝗿𝗶𝗰𝗲 ➛</b> 𝟯𝟬$'
)

_BUY_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💎 𝗣𝗮𝘆 𝗩𝗶𝗮', callback_data="menu_payment_methods")]
])

@router.message(F.text.startswith("/buy"))
async def buy_command(message: types.Message):
    await message.reply(text=_BUY_TEXT, parse_mode="HTML", reply_markup=_BUY_KB)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /sub - Grant Premium
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _sub_db_sync(target_id, display_name, plan_name, days, credits, amount):
    expiry_date = datetime.now() + timedelta(days=days)
    receipt_id = generate_receipt_id()
    
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    users = db["USERSDB"]
    
    try:
        users.update_one(
            {"user_id": target_id},
            {"$setOnInsert": {
                "user_id": target_id,
                "username": "Unknown",
                "first_name": display_name,
                "credits": 0,
                "is_premium": 1,
                "premium_expiry": expiry_date.isoformat(),
                "joined_at": datetime.now().isoformat(),
                "cc_checked": 0,
                "cc_charged": 0
            }},
            upsert=True
        )
        
        users.update_one(
            {"user_id": target_id},
            {"$set": {
                "first_name": display_name,
                "is_premium": 1,
                "premium_expiry": expiry_date.isoformat()
            }}
        )
        
        users.update_one(
            {"user_id": target_id},
            {"$inc": {"credits": credits}}
        )
        
        client.close()
        return receipt_id
    except Exception as e:
        client.close()
        logging.error(f"_sub_db_sync error: {e}")
        raise

@router.message(F.text.startswith("/sub"))
async def sub_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        await message.reply("❌ 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱.")
        return

    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply("❌ 𝗨𝘀𝗮𝗴𝗲: /sub {user_id/username} {plan}\nPlans: core, elite, root")
        return

    target_input, plan = args[0], args[1].lower()
    plan_map = {"core": ("Core 🛠️", 7, 13000, 10), "elite": ("Elite ⭐", 15, 23000, 15), "root": ("Root 👑", 30, 53000, 30)}
    if plan not in plan_map:
        await message.reply("❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗽𝗹𝗮𝗻. 𝗣𝗹𝗮𝗻𝘀: Core, Elite, Root")
        return

    target_id = await asyncio.to_thread(_resolve_user_id_sync, target_input)
    if not target_id:
        await message.reply("❌ 𝗖𝗼𝘂𝗹𝗱 𝗻𝗼𝘁 𝗳𝗶𝗻𝗱 𝘂𝘀𝗲𝗿.")
        return

    plan_name, days, credits, amount = plan_map[plan]
    display_name = "User"
    try:
        chat = await message.bot.get_chat(target_id)
        display_name = chat.first_name or chat.username or "User"
    except Exception:
        pass

    try:
        receipt_id = await asyncio.to_thread(_sub_db_sync, target_id, display_name, plan_name, days, credits, amount)
    except Exception as e:
        logging.error(f"sub error: {e}")
        await message.reply("❌ 𝗗𝗮𝘁𝗮𝗯𝗮𝘀𝗲 𝗘𝗿𝗿𝗼𝗿.")
        return

    user_link = f'<a href="tg://user?id={target_id}">{display_name}</a>'
    await message.reply(f"✅ Premium granted to {user_link} for {days} days with {credits:,} credits.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /info - User Info
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.message(F.text.startswith("/info"))
async def info_command(message: types.Message):
    user = message.from_user
    u_row = await asyncio.to_thread(get_user, user.id)
    
    if not u_row:
        await message.reply("User not found in database.")
        return
    
    text = (
        f"📊 <b>Your Info</b>\n\n"
        f"ID: <code>{user.id}</code>\n"
        f"Credits: <b>{u_row.get('credits', 0):,}</b>\n"
        f"Premium: <b>{'✅ Yes' if u_row.get('is_premium', 0) == 1 else '❌ No'}</b>\n"
        f"Joined: {u_row.get('joined_at', 'N/A')}"
    )
    await message.reply(text, parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /claim
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _claim_db_sync(user_id, code):
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    codes = db["GCDB"]
    users = db["USERSDB"]
    
    try:
        row = codes.find_one({"code": code})
        if not row:
            client.close()
            return "invalid", None
        if row.get('claimed_by') is not None:
            client.close()
            return "claimed", None
        is_prem, _ = get_premium_status(user_id)
        if is_prem:
            client.close()
            return "premium", None
        credits = row.get('credits', 0)
        codes.update_one(
            {"code": code},
            {"$set": {"claimed_by": user_id, "claimed_at": datetime.now().isoformat()}}
        )
        users.update_one(
            {"user_id": user_id},
            {"$inc": {"credits": credits}}
        )
        client.close()
        return "ok", credits
    except Exception as e:
        client.close()
        logging.error(f"claim error: {e}")
        return "error", None

@router.message(F.text.startswith("/claim"))
async def claim_command(message: types.Message):
    user = message.from_user
    args = message.text.split()[1:]

    if not args:
        await message.reply("❌ 𝗨𝘀𝗮𝗴𝗲: /claim {code}")
        return

    code = args[0].upper()
    status, credits = await asyncio.to_thread(_claim_db_sync, user.id, code)

    messages = {
        "invalid": "❌ Invalid code.",
        "claimed": "❌ This code has already been claimed.",
        "premium": "❌ Premium users cannot redeem codes.",
        "ok": f"✅ Successfully claimed {credits} credits!",
        "error": "❌ Error claiming code. Contact support.",
    }
    await message.reply(messages.get(status, "❌ Unknown error."))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /adcr - Add Credits
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _adcr_db_sync(target_id, add_credits):
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    users = db["USERSDB"]
    
    try:
        users.update_one(
            {"user_id": target_id},
            {"$setOnInsert": {
                "user_id": target_id,
                "username": "Unknown",
                "first_name": "User",
                "credits": 0,
                "is_premium": 0,
                "joined_at": datetime.now().isoformat(),
                "cc_checked": 0,
                "cc_charged": 0
            }},
            upsert=True
        )
        
        users.update_one(
            {"user_id": target_id},
            {"$inc": {"credits": add_credits}}
        )
        
        updated = users.find_one({"user_id": target_id}, {"credits": 1})
        new_total = updated.get("credits", 0) if updated else 0
        client.close()
        return new_total
    except Exception as e:
        client.close()
        logging.error(f"_adcr_db_sync error: {e}")
        raise

@router.message(F.text.startswith("/adcr"))
async def adcr_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        await message.reply("❌ Not authorized.")
        return

    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply("❌ 𝗨𝘀𝗮𝗴𝗲: /adcr {user_id} {amount}")
        return

    try:
        add_credits = int(args[1])
        if add_credits <= 0:
            await message.reply("❌ Amount must be positive.")
            return
    except ValueError:
        await message.reply("❌ Invalid amount.")
        return

    target_id = await asyncio.to_thread(_resolve_user_id_sync, args[0])
    if not target_id:
        await message.reply("❌ User not found.")
        return

    display_name = "User"
    try:
        chat = await message.bot.get_chat(target_id)
        display_name = chat.first_name or chat.username or "User"
    except Exception:
        pass

    try:
        new_total = await asyncio.to_thread(_adcr_db_sync, target_id, add_credits)
    except Exception as e:
        logging.error(f"adcr error: {e}")
        await message.reply("❌ Database error.")
        return

    user_link = f'<a href="tg://user?id={target_id}">{display_name}</a>'
    await message.reply(
        f"✅ Added <b>{add_credits:,}</b> credits to {user_link}.\n"
        f"New Total ➛ <b>{new_total:,}</b>",
        parse_mode="HTML"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /rsub - Remove Premium
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _rsub_db_sync(target_id):
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    users = db["USERSDB"]
    
    try:
        users.update_one(
            {"user_id": target_id},
            {"$set": {"is_premium": 0, "premium_expiry": None, "credits": 150}}
        )
        client.close()
        return True
    except Exception as e:
        client.close()
        logging.error(f"_rsub_db_sync error: {e}")
        raise

@router.message(F.text.startswith("/rsub"))
async def rsub_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        await message.reply("❌ Not authorized.")
        return

    args = message.text.split()[1:]
    if not args:
        await message.reply("❌ 𝗨𝘀𝗮𝗴𝗲: /rsub {user_id/username}")
        return

    target_id = await asyncio.to_thread(_resolve_user_id_sync, args[0])
    if not target_id:
        await message.reply("❌ User not found.")
        return

    try:
        await asyncio.to_thread(_rsub_db_sync, target_id)
    except Exception as e:
        logging.error(f"rsub error: {e}")
        await message.reply("❌ Database error.")
        return

    await message.reply(f"✅ Premium removed from {target_id} and credits reset to 150.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /g_code - Generate Codes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _g_code_db_sync(amount):
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    codes = db["GCDB"]
    
    generated = []
    try:
        for _ in range(amount):
            code = "CARD-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            codes.insert_one({
                "code": code,
                "credits": 100,
                "claimed_by": None,
                "claimed_at": None,
                "created_at": datetime.now().isoformat()
            })
            generated.append(code)
        client.close()
        return generated
    except Exception as e:
        client.close()
        logging.error(f"_g_code_db_sync error: {e}")
        return generated

@router.message(F.text.startswith("/g_code"))
async def g_code_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        await message.reply("❌ Not authorized.")
        return

    args = message.text.split()[1:]
    if not args:
        await message.reply("❌ 𝗨𝘀𝗮𝗴𝗲: /g_code {amount}")
        return

    try:
        amount = int(args[0])
        if amount <= 0:
            await message.reply("❌ Amount must be positive.")
            return
    except ValueError:
        await message.reply("❌ Invalid amount.")
        return

    generated_codes = await asyncio.to_thread(_g_code_db_sync, amount)
    if not generated_codes:
        await message.reply("❌ Failed to generate codes.")
        return

    formatted = "\n".join([f"<code>{c}</code>" for c in generated_codes])
    await message.reply(
        f"Generated {amount} codes (100 credits each):\n\n{formatted}\n\nUse /claim <code>",
        parse_mode="HTML"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /suball - List All Premium Users
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _suball_db_sync():
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    users = db["USERSDB"]
    
    try:
        rows = list(users.find({"is_premium": 1}))
        client.close()
        return rows
    except Exception as e:
        client.close()
        logging.error(f"_suball_db_sync error: {e}")
        return []

@router.message(F.text.startswith("/suball"))
async def suball_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        return

    rows = await asyncio.to_thread(_suball_db_sync)
    if not rows:
        await message.reply("No premium users found.")
        return

    output = io.BytesIO()
    output.write("Premium Users List\n\n".encode('utf-8'))
    for row in rows:
        expiry = row.get('premium_expiry', 'N/A')
        if expiry and isinstance(expiry, str):
            expiry = expiry[:10]
        line = (
            f"ID: {row.get('user_id')}\n"
            f"Username: {row.get('username') or 'N/A'}\n"
            f"Credits: {row.get('credits', 0)}\n"
            f"Expiry: {expiry}\n"
            f"{'-'*30}\n"
        ).encode('utf-8')
        output.write(line)

    filename = f"premium_users_{datetime.now().strftime('%Y%m%d')}.txt"
    document = BufferedInputFile(output.getvalue(), filename=filename)
    await message.reply_document(document=document)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /rc - Receipt Check (simplified)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.message(F.text.startswith("/rc"))
async def rc_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        await message.reply("❌ 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱.")
        return

    args = message.text.split()[1:]
    if not args:
        await message.reply("❌ 𝗨𝘀𝗮𝗴𝗲: /rc {receipt_id}")
        return

    receipt_id = args[0]
    await message.reply(f"🔍 Receipt {receipt_id} (Check in MongoDB manually)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /clear_codes - Remove claimed codes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _clear_claimed_codes_sync():
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    codes = db["GCDB"]
    
    try:
        result = codes.delete_many({"claimed_by": {"$ne": None}})
        client.close()
        return result.deleted_count
    except Exception as e:
        client.close()
        logging.error(f"_clear_claimed_codes_sync error: {e}")
        return 0

@router.message(F.text.startswith("/clear_codes"))
async def clear_codes_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        await message.reply("❌ Not authorized.")
        return

    deleted = await asyncio.to_thread(_clear_claimed_codes_sync)
    await message.reply(f"✅ Deleted {deleted} claimed codes.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /codes - List all codes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _list_codes_sync():
    from pymongo import MongoClient
    client = MongoClient("mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject")
    db = client["MASTER_DATABASE"]
    codes = db["GCDB"]
    
    try:
        rows = list(codes.find().sort("created_at", -1))
        client.close()
        return rows
    except Exception as e:
        client.close()
        logging.error(f"_list_codes_sync error: {e}")
        return []

@router.message(F.text.startswith("/codes"))
async def list_codes_command(message: types.Message):
    user = message.from_user
    if user.id != ADMIN_ID:
        await message.reply("❌ Not authorized.")
        return

    rows = await asyncio.to_thread(_list_codes_sync)
    if not rows:
        await message.reply("No codes found.")
        return

    output = io.BytesIO()
    output.write("Codes List\n\n".encode('utf-8'))
    for row in rows:
        status = "Used" if row.get('claimed_by') else "Available"
        claimed_by = row.get('claimed_by') or "N/A"
        claimed_at = row.get('claimed_at') or "N/A"
        line = (
            f"Code: {row.get('code')}\n"
            f"Credits: {row.get('credits')}\n"
            f"Status: {status}\n"
            f"Claimed By: {claimed_by}\n"
            f"Claimed At: {claimed_at}\n"
            f"{'-'*30}\n"
        ).encode('utf-8')
        output.write(line)

    document = BufferedInputFile(output.getvalue(), filename=f"codes_{datetime.now().strftime('%Y%m%d')}.txt")
    await message.reply_document(document=document)
