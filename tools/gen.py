"""
Card Generator Tool
Command: /gen
Usage: /gen {bin} {quantity}
Example: /gen 514377 10
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import random
import re
import logging
import requests

router = Router()

def luhn_generate(bin_prefix, length=16):
    """Generate a valid credit card number using Luhn algorithm"""
    if len(bin_prefix) > length:
        bin_prefix = bin_prefix[:length]
    
    card = bin_prefix
    while len(card) < length - 1:
        card += str(random.randint(0, 9))
    
    def luhn_checksum(card_number):
        total = 0
        reverse_digits = card_number[::-1]
        for i, d in enumerate(reverse_digits):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10
    
    checksum = luhn_checksum(card + "0")
    check_digit = (10 - checksum) % 10
    return card + str(check_digit)

def get_bin_info(bin_num):
    """Fetch BIN info from binlist.net"""
    try:
        resp = requests.get(f'https://lookup.binlist.net/{bin_num}', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'scheme': data.get('scheme', 'Unknown'),
                'type': data.get('type', 'Unknown'),
                'bank': data.get('bank', {}).get('name', 'Unknown'),
                'country': data.get('country', {}).get('name', 'Unknown'),
                'emoji': data.get('country', {}).get('emoji', ''),
            }
    except:
        pass
    return None

@router.message(Command("gen"))
async def gen_command(message: types.Message):
    args = message.text.split()[1:]
    
    if not args:
        await message.reply(
            "💳 <b>𝗖𝗮𝗿𝗱 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗼𝗿</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱: <code>/gen</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 𝗨𝘀𝗮𝗴𝗲: <code>/gen {BIN} {quantity}</code>\n\n"
            "📝 𝗘𝘅𝗮𝗺𝗽𝗹𝗲: <code>/gen 514377 10</code>\n"
            "📝 𝗘𝘅𝗮𝗺𝗽𝗹𝗲: <code>/gen 411111 5</code>",
            parse_mode="HTML"
        )
        return
    
    bin_input = args[0]
    quantity = 10
    
    if len(args) > 1:
        try:
            quantity = int(args[1])
            if quantity > 100:
                quantity = 100
                await message.reply("⚠️ <b>𝗟𝗶𝗺𝗶𝘁𝗲𝗱 𝘁𝗼 𝟭𝟬𝟬 𝗰𝗮𝗿𝗱𝘀</b>", parse_mode="HTML")
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 10
    
    bin_clean = re.sub(r'\D', '', bin_input)
    if len(bin_clean) < 6:
        await message.reply("❌ <b>𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗕𝗜𝗡</b>\nBIN must be at least 6 digits.", parse_mode="HTML")
        return
    
    bin_clean = bin_clean[:6]
    
    # Generate cards
    cards = []
    for _ in range(quantity):
        card = luhn_generate(bin_clean)
        exp_month = str(random.randint(1, 12)).zfill(2)
        exp_year = str(random.randint(25, 35))
        cvv = str(random.randint(100, 999))
        cards.append(f"{card}|{exp_month}|{exp_year}|{cvv}")
    
    # Get BIN info
    bin_info = get_bin_info(bin_clean)
    
    if bin_info:
        brand = bin_info.get('scheme', 'Unknown')
        bank = bin_info.get('bank', 'Unknown')
        country = bin_info.get('country', 'Unknown')
        emoji = bin_info.get('emoji', '')
        card_type = bin_info.get('type', 'Unknown')
        
        header = (
            f"💳 <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 𝗖𝗮𝗿𝗱𝘀</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>𝗕𝗜𝗡:</b> <code>{bin_clean}</code>\n"
            f"<b>𝗕𝗿𝗮𝗻𝗱:</b> {brand}\n"
            f"<b>𝗧𝘆𝗽𝗲:</b> {card_type}\n"
            f"<b>𝗕𝗮𝗻𝗸:</b> {bank}\n"
            f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {emoji} {country}\n"
            f"<b>𝗤𝘂𝗮𝗻𝘁𝗶𝘁𝘆:</b> {quantity}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
        )
    else:
        header = (
            f"💳 <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 𝗖𝗮𝗿𝗱𝘀</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>𝗕𝗜𝗡:</b> <code>{bin_clean}</code>\n"
            f"<b>𝗤𝘂𝗮𝗻𝘁𝗶𝘁𝘆:</b> {quantity}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
        )
    
    card_list = "\n".join([f"<code>{c}</code>" for c in cards])
    
    if quantity > 20:
        file_content = "\n".join(cards)
        txt_file = BufferedInputFile(file=file_content.encode('utf-8'), filename=f"cards_{bin_clean}.txt")
        
        await message.reply(header + f"📄 <b>Cards saved to file</b>", parse_mode="HTML")
        await message.reply_document(
            document=txt_file,
            caption=f"💳 {quantity} cards generated for BIN {bin_clean}"
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 𝗕𝗨𝗬 𝗡𝗢𝗪", url="https://t.me/npnbit4")]
        ])
        
        await message.reply(
            header + card_list,
            parse_mode="HTML",
            reply_markup=kb
        )

# Also handle /b_gen
@router.message(Command("b_gen"))
async def b_gen_command(message: types.Message):
    await gen_command(message)
