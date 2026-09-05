"""
GATE_NAME Mass Checker
Command: /CMD
Type: TYPE
Limits: Free: 10 | Premium: Unlimited
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import asyncio
import time
import logging
import os
import random
from datetime import datetime

from database import get_user_credits, update_credits, get_user
from sub import get_premium_status
from bin import get_bin_info
from mass_gates.card_cleaner import clean_cards, mask_card

# Import from single gate
from gates.GATE_FILE import GATE_FUNCTION

router = Router()
GATE_NAME = "GATE_DISPLAY_NAME"
GATE_CMD = "CMD_NAME"
active_sessions = {}

def get_bin_data(bin_num):
    try:
        import requests
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

async def process_single_card(card):
    # Call the gate function - to be customized per gate
    # Return: {"status": "APPROVED/DECLINED/ERROR", "response": "message"}
    pass

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
    
    pct = int((checked / total) * 100) if total > 0 else 0
    
    display_card = mask_card(current_card) if current_card else "—"
    status_emoji = "✅" if "APPROVED" in current_status else ("❌" if "DECLINED" in current_status else ("⚠️" if "ERROR" in current_status else "⏳"))
    
    text = (
        f"📦 <b>𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 𝗟𝗶𝘃𝗲</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>{pct}%</b> | {checked:,} / {total:,}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱: {approved:,}\n"
        f"❌ 𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱: {declined:,}\n"
        f"⚠️ 𝗘𝗿𝗿𝗼𝗿𝘀: {errors:,}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ 𝗪𝗼𝗿𝗸𝗲𝗿𝘀: {workers}\n"
        f"⏳ 𝗖𝗵𝗲𝗰𝗸𝗲𝗱: {checked:,} / {total:,}\n"
    )
    
    # Floating card button
    card_button = InlineKeyboardButton(
        text=f"{status_emoji} {display_card}",
        callback_data=f"{GATE_CMD}_card_{session_data['user_id']}"
    )
    
    # Floating response button
    response_text = current_response[:40] + '...' if len(current_response) > 40 else current_response
    response_button = InlineKeyboardButton(
        text=f"📝 {response_text or 'Waiting...'}",
        callback_data=f"{GATE_CMD}_response_{session_data['user_id']}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [card_button],
        [response_button],
        [
            InlineKeyboardButton(text=f"⏸️ 𝗣𝗮𝘂𝘀𝗲", callback_data=f"{GATE_CMD}_pause_{session_data['user_id']}"),
            InlineKeyboardButton(text=f"🛑 𝗦𝘁𝗼𝗽", callback_data=f"{GATE_CMD}_stop_{session_data['user_id']}")
        ]
    ])
    
    return text, kb

@router.message(Command(GATE_CMD))
async def mass_command(message: types.Message):
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
            f"📦 <b>𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸𝗲𝗿</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱: <code>/{GATE_CMD}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>𝗨𝘀𝗮𝗴𝗲:</b>\n"
            f"1️⃣ Paste cards after /{GATE_CMD}\n"
            f"2️⃣ Reply to .txt file\n"
            f"3️⃣ Reply to text message\n\n"
            f"📌 <b>𝗙𝗼𝗿𝗺𝗮𝘁:</b>\n"
            f"<code>CC|MM|YY|CVV</code>\n\n"
            f"📌 <b>𝗟𝗶𝗺𝗶𝘁𝘀:</b>\n"
            f"┣ 𝗙𝗿𝗲𝗲: <b>𝟭𝟬</b> 𝗰𝗮𝗿𝗱𝘀\n"
            f"┗ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: <b>𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱</b>",
            parse_mode="HTML"
        )
        return
    
    if len(raw_cards) > 0:
        await message.answer(f"✅ Cleaned {len(raw_cards)} valid cards from your input.")
    
    is_premium, _ = await asyncio.to_thread(get_premium_status, user_id)
    limit = 10000 if is_premium else 10
    if len(raw_cards) > limit:
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
        session_data['current_status'] = '⏳ Processing...'
        session_data['current_response'] = ''
        
        text, kb = build_live_message(session_data)
        try:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            pass
        
        result = await process_single_card(card)
        
        session_data['checked'] += 1
        session_data['current_response'] = result['response']
        session_data['current_status'] = result['status']
        
        if "APPROVED" in result['status']:
            session_data['approved'] += 1
            session_data['approved_cards'].append(card)
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
                f"𝗨𝘀𝗲𝗿 ➛ {user_link} (TRIAL)\n"
                f"𝗗𝗲𝘃 ➛ npnbit4"
            )
            await message.answer(approved_msg, parse_mode="HTML")
        elif "DECLINED" in result['status']:
            session_data['declined'] += 1
            session_data['declined_cards'].append(card)
        else:
            session_data['errors'] += 1
            session_data['error_cards'].append(card)
        
        text, kb = build_live_message(session_data)
        try:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            pass
        
        await asyncio.sleep(0.3)
    
    if not session_data.get('stop', False):
        text, kb = build_live_message(session_data)
        text += f"\n\n✅ 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲!"
        try:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=None)
        except:
            pass
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if session_data['approved_cards']:
            approved_txt = f"APPROVED_{timestamp}.txt"
            with open(approved_txt, "w", encoding="utf-8") as f:
                f.write("\n".join(session_data['approved_cards']))
            await message.reply_document(
                document=FSInputFile(approved_txt),
                caption=f"✅ Approved: {len(session_data['approved_cards'])} cards"
            )
            os.remove(approved_txt)
        
        if session_data['declined_cards']:
            declined_txt = f"DECLINED_{timestamp}.txt"
            with open(declined_txt, "w", encoding="utf-8") as f:
                f.write("\n".join(session_data['declined_cards']))
            await message.reply_document(
                document=FSInputFile(declined_txt),
                caption=f"❌ Declined: {len(session_data['declined_cards'])} cards"
            )
            os.remove(declined_txt)
        
        if session_data['error_cards']:
            error_txt = f"ERRORS_{timestamp}.txt"
            with open(error_txt, "w", encoding="utf-8") as f:
                f.write("\n".join(session_data['error_cards']))
            await message.reply_document(
                document=FSInputFile(error_txt),
                caption=f"⚠️ Errors: {len(session_data['error_cards'])} cards"
            )
            os.remove(error_txt)
    
    active_sessions.pop(user_id, None)

@router.callback_query(F.data.startswith(f"{GATE_CMD}_card_"))
async def card_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Not your session!", show_alert=True)
        return
    session = active_sessions.get(user_id)
    if not session:
        await callback.answer("⚠️ No active session", show_alert=True)
        return
    card = session.get('current_card', 'No card')
    await callback.answer(f"📌 {card[:40]}", show_alert=True)

@router.callback_query(F.data.startswith(f"{GATE_CMD}_response_"))
async def response_callback(callback: types.CallbackQuery):
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
    await callback.answer(f"📊 {status}: {response[:100]}", show_alert=True)

@router.callback_query(F.data.startswith(f"{GATE_CMD}_stop_"))
async def stop_callback(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Not your session!", show_alert=True)
        return
    if user_id in active_sessions:
        active_sessions[user_id]['stop'] = True
        await callback.answer("🛑 Stopping...", show_alert=True)
    else:
        await callback.answer("⚠️ No active session", show_alert=True)

@router.callback_query(F.data.startswith(f"{GATE_CMD}_pause_"))
async def pause_callback(callback: types.CallbackQuery):
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
