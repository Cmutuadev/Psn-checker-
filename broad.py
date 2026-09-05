import asyncio
import logging
import time
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from pymongo import MongoClient

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADMIN_ID = 6152006521

# Edit the live counter at most once every N seconds (no flood)
UPDATE_INTERVAL = 10

router = Router()

# Guard: prevents a second broadcast firing while one is already in progress
_broadcast_running = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB HELPER (MONGODB)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MONGO_URI = "mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject"

def _get_all_user_ids() -> list:
    client = MongoClient(MONGO_URI)
    db = client["MASTER_DATABASE"]
    users = db["USERSDB"]
    
    try:
        rows = users.find({}, {"user_id": 1})
        user_ids = [row.get("user_id") for row in rows if row.get("user_id")]
        client.close()
        return user_ids
    except Exception as e:
        client.close()
        logging.error(f"_get_all_user_ids error: {e}")
        return []

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LIVE STATUS BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _status_text(total: int, done: int, sent: int, blocked: int, failed: int, finished: bool = False) -> str:
    header = "✅ <b>Broadcast Complete</b>" if finished else "📡 <b>Broadcasting…</b>"
    bar_filled = int((done / total) * 20) if total else 20
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total</b>   ➛ <b>{total}</b>\n"
        f"📨 <b>Sent</b>    ➛ <b>{sent}</b>\n"
        f"🚫 <b>Blocked</b> ➛ <b>{blocked}</b>\n"
        f"❌ <b>Failed</b>  ➛ <b>{failed}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<code>[{bar}]</code> {done}/{total}"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /broad COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.message(Command("broad"))
async def broad_command(message: types.Message):
    global _broadcast_running

    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ Admin only.")
        return

    if not message.reply_to_message:
        await message.reply(
            "↩️ Reply to a message with <b>/broad</b> to broadcast it to all users.\n\n"
            "<i>The message is sent as a native bot message — no 'Forwarded from' header.</i>",
            parse_mode="HTML"
        )
        return

    if _broadcast_running:
        await message.reply("⚠️ A broadcast is already in progress. Please wait for it to finish.")
        return

    _broadcast_running = True
    try:
        user_ids = await asyncio.to_thread(_get_all_user_ids)
        total = len(user_ids)
        target = message.reply_to_message

        if total == 0:
            await message.reply("⚠️ No users found in database.")
            _broadcast_running = False
            return

        status_msg = await message.reply(
            _status_text(total, 0, 0, 0, 0),
            parse_mode="HTML"
        )

        sent = blocked = failed = 0
        last_update = time.monotonic()

        for idx, uid in enumerate(user_ids, start=1):
            try:
                await target.copy_to(chat_id=uid)
                sent += 1

            except TelegramForbiddenError:
                blocked += 1
                logging.debug(f"[broad] blocked by {uid}")

            except TelegramBadRequest as e:
                failed += 1
                logging.debug(f"[broad] bad request for {uid}: {e}")

            except Exception as e:
                failed += 1
                logging.debug(f"[broad] error for {uid}: {e}")

            now = time.monotonic()
            if now - last_update >= UPDATE_INTERVAL:
                try:
                    await status_msg.edit_text(
                        _status_text(total, idx, sent, blocked, failed),
                        parse_mode="HTML"
                    )
                    last_update = now
                except Exception:
                    pass

            await asyncio.sleep(0.05)

        await status_msg.edit_text(
            _status_text(total, total, sent, blocked, failed, finished=True),
            parse_mode="HTML"
        )

    finally:
        _broadcast_running = False
