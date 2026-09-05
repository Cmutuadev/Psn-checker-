"""
PayPal Gate - DISABLED
Command: /pp
Status: Under Maintenance
"""

from aiogram import Router, F, types
from aiogram.filters import Command

router = Router()

@router.message(Command("pp"))
async def pp_command(message: types.Message):
    await message.reply(
        "🚧 <b>𝗣𝗮𝘆𝗣𝗮𝗹 𝗚𝗮𝘁𝗲 𝗶𝘀 𝗨𝗻𝗱𝗲𝗿 𝗠𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲</b>\n\n"
        "⏳ 𝗪𝗲'𝗹𝗹 𝗯𝗲 𝗯𝗮𝗰𝗸 𝘀𝗼𝗼𝗻 𝘄𝗶𝘁𝗵 𝗶𝗺𝗽𝗿𝗼𝘃𝗲𝗺𝗲𝗻𝘁𝘀!\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ 𝗢𝘁𝗵𝗲𝗿 𝗴𝗮𝘁𝗲𝘀 𝗮𝗿𝗲 𝗮𝗰𝘁𝗶𝘃𝗲:\n"
        "┣ /sh - Shopify\n"
        "┣ /st - Stripe\n"
        "┣ /chk - Stripe Auth\n"
        "┗ /vbv - Braintree VBV\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "𝗗𝗲𝘃: @npnbit4",
        parse_mode="HTML"
    )
