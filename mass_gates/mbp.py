"""
BluePay Mass Checker
Command: /mbp
Type: Mass Charge
Limits: Free: 10 | Premium: Unlimited
"""

from aiogram import Router, F, types
from aiogram.filters import Command
import asyncio
import time
import logging

router = Router()

@router.message(Command("mbp"))
async def mbp_command(message: types.Message):
    await message.answer(
        "📦 <b>𝗕𝗹𝘂𝗲𝗣𝗮𝘆 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸𝗲𝗿</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱: <code>/mbp</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>𝗨𝘀𝗮𝗴𝗲:</b>\n"
        "𝗥𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 .𝘁𝘅𝘁 𝗳𝗶𝗹𝗲 𝘄𝗶𝘁𝗵 𝗰𝗮𝗿𝗱 𝗹𝗶𝘀𝘁\n\n"
        "📌 <b>𝗙𝗼𝗿𝗺𝗮𝘁:</b>\n"
        "<code>CC|MM|YY|CVV</code> (𝗼𝗻𝗲 𝗽𝗲𝗿 𝗹𝗶𝗻𝗲)\n\n"
        "📌 <b>𝗟𝗶𝗺𝗶𝘁𝘀:</b>\n"
        "┣ 𝗙𝗿𝗲𝗲: <b>𝟭𝟬</b> 𝗰𝗮𝗿𝗱𝘀\n"
        "┗ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: <b>𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱</b>",
        parse_mode="HTML"
    )

@router.message(Command("mbp"))
async def mbp_command(message: types.Message):
    await message.answer(
        "📦 <b>𝗕𝗹𝘂𝗲𝗣𝗮𝘆 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸𝗲𝗿</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱: <code>/mbp</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>𝗨𝘀𝗮𝗴𝗲:</b>\n"
        "𝗥𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 .𝘁𝘅𝘁 𝗳𝗶𝗹𝗲 𝘄𝗶𝘁𝗵 𝗰𝗮𝗿𝗱 𝗹𝗶𝘀𝘁\n\n"
        "📌 <b>𝗟𝗶𝗺𝗶𝘁𝘀:</b>\n"
        "┣ 𝗙𝗿𝗲𝗲: <b>𝟭𝟬</b> 𝗰𝗮𝗿𝗱𝘀\n"
        "┗ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: <b>𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱</b>",
        parse_mode="HTML"
    )
