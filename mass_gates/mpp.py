"""
PayPal Mass - DISABLED
Command: /mpp
Status: Under Maintenance
"""

from aiogram import Router, F, types
from aiogram.filters import Command

router = Router()

@router.message(Command("mpp"))
async def mpp_command(message: types.Message):
    await message.reply(
        "🚧 <b>𝗣𝗮𝘆𝗣𝗮𝗹 𝗠𝗮𝘀𝘀 𝗚𝗮𝘁𝗲 𝗶𝘀 𝗨𝗻𝗱𝗲𝗿 𝗠𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲</b>\n\n"
        "⏳ 𝗪𝗲'𝗹𝗹 𝗯𝗲 𝗯𝗮𝗰𝗸 𝘀𝗼𝗼𝗻!\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ 𝗢𝘁𝗵𝗲𝗿 𝗺𝗮𝘀𝘀 𝗴𝗮𝘁𝗲𝘀 𝗮𝗿𝗲 𝗮𝗰𝘁𝗶𝘃𝗲:\n"
        "┣ /msh - Shopify\n"
        "┣ /mst - Stripe\n"
        "┗ /mchk - Stripe Auth\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "𝗗𝗲𝘃: @npnbit4",
        parse_mode="HTML"
    )
