"""
PayU Mass Checker - UNDER MAINTENANCE
Command: /mpyu
Status: Temporarily disabled
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()
GATE_NAME = "PayU"
GATE_CMD = "mpyu"

@router.message(Command("mpyu"))
async def mpyu_command(message: types.Message):
    await message.answer(
        f"⛔️ <b>{GATE_NAME} Mass Checker</b>\n\n"
        f"🔧 <b>UNDER MAINTENANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛠 This gateway is currently being updated.\n"
        f"⏳ Please check back later.\n\n"
        f"📢 Contact: @npnbit4\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Other gates available:\n"
        f"┣ /msh - Shopify\n"
        f"┣ /mst - Stripe\n"
        f"┣ /mchk - Stripe Auth\n"
        f"┣ /mrc - Recurly\n"
        f"┣ /mau - MAU\n"
        f"┣ /mb3 - Braintree\n"
        f"┣ /mvbv - Braintree VBV\n"
        f"┗ /mrz - Razorpay",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 BUY PREMIUM", url="https://t.me/npnbit4")]
        ])
    )

@router.callback_query(F.data.startswith("mpyu_"))
async def mpyu_placeholder(callback: types.CallbackQuery):
    await callback.answer("⛔️ This gate is under maintenance", show_alert=True)
