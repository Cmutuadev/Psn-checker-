import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Awaitable

from aiogram import Bot, Dispatcher, types, F, Router, BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user, create_user, get_user_credits, update_credits
from gate import on_command, off_command
from fb import setup_feedback_handler, feedback_cmd, router as fb_router
from stats import stats_command
from tools.binn import binn_command
from tools.fake import router as fake_router, fake_command
from tools.gen import router as gen_router, gen_command
from cmds import cmds_command, router as cmds_router
from broad import broad_command, router as broad_router
from ban import ban_command, unban_command, BanMiddleware, router as ban_router
from status import vps_command, router as status_router

from sub import (
    sub_command, rc_command, suball_command, g_code_command,
    claim_command, info_command, rsub_command, buy_command, adcr_command
)
from proxy import proxy_command, checkproxy_command, clearproxy_command

from gates.st import st_command
from gates.sh import sh_command, sh_callback_handler
from gates.sp import sp_command
from gates.hc import hc_command
from gates.pf import pf_command
from gates.vbv import vbv_command
from gates.ft import ft_command
from gates.bl import bl_command
from gates.pp import pp_command
from gates.at import at_command
from gates.pw import pw_command
from gates.rz import rz_command
from gates.pyu import pyu_command
from gates.chk import chk_command
from gates.b3 import b3_command
from gates.nmi import nmi_command
from gates.nmi2 import nmi2_command

# NEW GATES
from gates.au import au_command
from gates.sl import sl_command
from gates.rc import rc_command
from gates.s1 import s1_command

# AUTO HITTER
from autohitters.stco import stco_command, stco_callback_handler

# MASS GATE IMPORTS
from mass_gates.msh import router as msh_router
from mass_gates.mst import router as mst_router, mst_command
from mass_gates.mchk import router as mchk_router, mchk_command
from mass_gates.mb3 import router as mb3_router, mb3_command
from mass_gates.mvbv import router as mvbv_router, mvbv_command
from mass_gates.mpp import router as mpp_router, mpp_command
from mass_gates.mhc import router as mhc_router
from mass_gates.msp import router as msp_router
from mass_gates.mpf import router as mpf_router, mpf_command
from mass_gates.mft import router as mft_router, mft_command
from mass_gates.mnmi import router as mnmi_router, mnmi_command
from mass_gates.mnmi2 import router as mnmi2_router, mnmi2_command
from mass_gates.mbl import router as mbl_router, mbl_command
from mass_gates.mat import router as mat_router, mat_command
from mass_gates.mpw import router as mpw_router, mpw_command
from mass_gates.mrz import router as mrz_router, mrz_command
from mass_gates.mpyu import router as mpyu_router

# NEW MASS GATES
from mass_gates.mau import router as mau_router, mau_command
from mass_gates.msl import router as msl_router, msl_command
from mass_gates.mbp import router as mbp_router, mbp_command
from mass_gates.mrc import router as mrc_router, mrc_command
from mass_gates.ms1 import router as ms1_router, ms1_command

from mass_gates.sitechk import (
    sitechk_command, addsite_command, siteall_command,
    removeall_command, dedupe_command, proxyinfo_command, resetproxy_command
)

import payments as pay_sys

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOT_TOKEN = "8087419884:AAGLU1JIpz_2rEOhXBgNxsfWwpVW24wORes"
START_IMAGE_URL = "https://i.ibb.co/6c0996jT/photo-5888528011563747370-c.jpg"
LOG_CHANNEL_ID = -1004408574006
BOT_LINK = "https://t.me/Eggemailbot"

REQUIRED_CHANNEL_ID = -1004406016532
REQUIRED_GROUP_ID = -1004408574006
CHANNEL_LINK = "https://t.me/+O8znr9FYc5tjZGQ1"
GROUP_LINK = "https://t.me/+H7t10pHre30xMmY1"

MAIN_GROUP_ID = -1004408574006

DEV_USERNAME = "npnbit4"
ADMIN_IDS = {6152006521}

JOIN_TEXT = (
    "⚠️ <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗥𝗲𝘀𝘁𝗿𝗶𝗰𝘁𝗲𝗱!</b>\n\n"
    "𝗧𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁 𝘆𝗼𝘂 𝗺𝘂𝘀𝘁 𝗷𝗼𝗶𝗻 𝗼𝘂𝗿 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗮𝗻𝗱 𝗴𝗿𝗼𝘂𝗽 𝗳𝗶𝗿𝘀𝘁.\n\n"
    "𝗖𝗹𝗶𝗰𝗸 𝗩𝗲𝗿𝗶𝗳𝘆 𝗮𝗳𝘁𝗲𝗿 𝗷𝗼𝗶𝗻𝗶𝗻𝗴 𝗯𝗼𝘁𝗵."
)

PRICING_TEXT = (
    f'<b>𝗔𝗰𝗰𝗲𝘀𝘀 ➛ 𝗖𝗢𝗥𝗘</b> <tg-emoji emoji-id="5379869575338812919">💎</tg-emoji>\n'
    f'<b>𝗦𝗽𝗮𝗻 ➛</b> [𝟳 𝗗𝗔𝗬𝗦]\n'
    f'<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛</b> 𝟭𝟯,𝟬𝟬𝟬\n'
    f'<b>𝗣𝗿𝗶𝗰𝗲 ➛</b> 𝟭𝟬$\n'
    f'━━━━━━━━━━━━━━━━\n'
    f'<b>𝗔𝗰𝗰𝗲𝘀𝘀 ➛ 𝗘𝗟𝗜𝗧𝗘</b> <tg-emoji emoji-id="5836898273666798437">💎</tg-emoji>\n'
    f'<b>𝗦𝗽𝗮𝗻 ➛</b> [𝟭𝟱 𝗗𝗔𝗬𝗦]\n'
    f'<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛</b> 𝟮𝟯,𝟬𝟬𝟬\n'
    f'<b>𝗣𝗿𝗶𝗰𝗲 ➛</b> 𝟭𝟱$\n'
    f'━━━━━━━━━━━━━━━━\n'
    f'<b>𝗔𝗰𝗰𝗲𝘀𝘀 ➛ 𝗥𝗢𝗢𝗧</b> <tg-emoji emoji-id="4956420911310832630">💎</tg-emoji>\n'
    f'<b>𝗦𝗽𝗮𝗻 ➛</b> [𝟯𝟬 𝗗𝗔𝗬𝗦]\n'
    f'<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛</b> 𝟱𝟯,𝟬𝟬𝟬\n'
    f'<b>𝗣𝗿𝗶𝗰𝗲 ➛</b> 𝟯𝟬$'
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ROUTER REGISTRATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

dp.include_router(msh_router)
dp.include_router(mst_router)
dp.include_router(mchk_router)
dp.include_router(mb3_router)
dp.include_router(mvbv_router)
dp.include_router(mpp_router)
dp.include_router(mhc_router)
dp.include_router(msp_router)
dp.include_router(mpf_router)
dp.include_router(mft_router)
dp.include_router(mnmi_router)
dp.include_router(mnmi2_router)
dp.include_router(mbl_router)
dp.include_router(mat_router)
dp.include_router(mpw_router)
dp.include_router(mrz_router)
dp.include_router(mpyu_router)
dp.include_router(mau_router)
dp.include_router(msl_router)
dp.include_router(mbp_router)
dp.include_router(mrc_router)
dp.include_router(ms1_router)
dp.include_router(cmds_router)
dp.include_router(fb_router)
dp.include_router(ban_router)
dp.include_router(broad_router)
dp.include_router(status_router)
dp.include_router(fake_router)
dp.include_router(gen_router)

router = Router()
dp.include_router(router)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MEMBERSHIP CACHE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MEMBERSHIP_CACHE: Dict[int, tuple] = {}
_MEMBERSHIP_CACHE_TTL = 60
_MEMBERSHIP_LOCK: Dict[int, asyncio.Lock] = {}
_MEMBERSHIP_LOCK_MAP_LOCK = asyncio.Lock()

_VALID_STATUSES = {"member", "administrator", "creator"}

async def _get_user_lock(user_id: int) -> asyncio.Lock:
    async with _MEMBERSHIP_LOCK_MAP_LOCK:
        if user_id not in _MEMBERSHIP_LOCK:
            _MEMBERSHIP_LOCK[user_id] = asyncio.Lock()
        return _MEMBERSHIP_LOCK[user_id]

async def check_membership(user_id: int, bot_instance: Bot) -> bool:
    now = time.monotonic()
    cached = _MEMBERSHIP_CACHE.get(user_id)
    if cached is not None:
        is_member, expires_at = cached
        if now < expires_at:
            return is_member

    lock = await _get_user_lock(user_id)
    async with lock:
        cached = _MEMBERSHIP_CACHE.get(user_id)
        if cached is not None:
            is_member, expires_at = cached
            if now < expires_at:
                return is_member

        try:
            ch, gr = await asyncio.gather(
                bot_instance.get_chat_member(REQUIRED_CHANNEL_ID, user_id),
                bot_instance.get_chat_member(REQUIRED_GROUP_ID, user_id),
            )
            is_member = ch.status in _VALID_STATUSES and gr.status in _VALID_STATUSES
        except Exception as e:
            logging.warning(f"Membership check failed for {user_id}: {e}")
            is_member = True

        ttl = _MEMBERSHIP_CACHE_TTL if is_member else 15
        _MEMBERSHIP_CACHE[user_id] = (is_member, now + ttl)
        return is_member

def invalidate_membership_cache(user_id: int):
    _MEMBERSHIP_CACHE.pop(user_id, None)

_JOIN_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", url=CHANNEL_LINK)],
    [InlineKeyboardButton(text="𝗝𝗼𝗶𝗻 𝗚𝗿𝗼𝘂𝗽", url=GROUP_LINK)],
    [InlineKeyboardButton(text="𝗩𝗲𝗿𝗶𝗳𝘆", callback_data="verify_membership")]
])

class MembershipMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data: Dict[str, Any]):
        user = event.from_user
        if not user:
            return await handler(event, data)
        if user.id in ADMIN_IDS:
            return await handler(event, data)
        
        if event.chat.id == MAIN_GROUP_ID:
            return await handler(event, data)
        
        if not await check_membership(user.id, data["bot"]):
            await event.reply(text=JOIN_TEXT, parse_mode="HTML", reply_markup=_JOIN_KB, disable_web_page_preview=True)
            return
        
        return await handler(event, data)

dp.message.middleware(MembershipMiddleware())
dp.message.middleware(BanMiddleware())

@router.callback_query(F.data == "verify_membership")
async def verify_membership_callback(callback: types.CallbackQuery):
    invalidate_membership_cache(callback.from_user.id)
    joined = await check_membership(callback.from_user.id, callback.bot)
    if joined:
        await asyncio.gather(
            callback.answer("✅ 𝗩𝗲𝗿𝗶𝗳𝗶𝗲𝗱! 𝗬𝗼𝘂 𝗻𝗼𝘄 𝗵𝗮𝘃𝗲 𝗳𝘂𝗹𝗹 𝗮𝗰𝗰𝗲𝘀𝘀.", show_alert=True),
            callback.message.delete(),
        )
    else:
        await callback.answer(
            "❌ 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲𝗻'𝘁 𝗷𝗼𝗶𝗻𝗲𝗱 𝘆𝗲𝘁!\n\n𝗣𝗹𝗲𝗮𝘀𝗲 𝗷𝗼𝗶𝗻 𝗯𝗼𝘁𝗵 𝘁𝗵𝗲 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗮𝗻𝗱 𝗴𝗿𝗼𝘂𝗽 𝗳𝗶𝗿𝘀𝘁, 𝘁𝗵𝗲𝗻 𝗰𝗹𝗶𝗰𝗸 𝗩𝗲𝗿𝗶𝗳𝘆.",
            show_alert=True
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB HELPERS (MONGODB)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _ensure_user_sync(user_id, username):
    try:
        if not get_user(user_id):
            create_user(user_id, username or "unknown")
        cr = get_user_credits(user_id)
        if not cr or cr == 0:
            update_credits(user_id, 150)
    except Exception as e:
        logging.error(f"ensure_user {user_id}: {e}")

async def ensure_user_and_credits(user_id, username="unknown"):
    await asyncio.to_thread(_ensure_user_sync, user_id, username)

def _status_sync(user_id):
    credits_str = "0"
    plan = "Trial"
    joined_str = "N/A"
    try:
        user = get_user(user_id)
        if user:
            joined_str = user.get("joined_at", "N/A")
            if isinstance(joined_str, datetime):
                joined_str = joined_str.strftime('%Y-%m-%d')
            elif isinstance(joined_str, str) and len(joined_str) > 10:
                joined_str = joined_str[:10]
            is_premium = user.get("is_premium", 0) == 1
            if is_premium:
                plan = user.get("plan", "Premium")
            credits = get_user_credits(user_id)
            credits_str = str(credits if credits is not None else 0)
    except Exception as e:
        logging.error(f"status {user_id}: {e}")
        credits = get_user_credits(user_id)
        credits_str = str(credits if credits is not None else 0)
    return credits_str, plan, joined_str

async def _get_caption(user) -> str:
    credits_str, access_str, joined_str = await asyncio.to_thread(_status_sync, user.id)
    ul = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    dl = f'<a href="https://t.me/{DEV_USERNAME}">@{DEV_USERNAME}</a>'
    return (
        f"𝗨𝘀𝗲𝗿 ➛ {ul}\n"
        f"𝗨𝘀𝗲𝗿 𝗜𝗗 ➛ <code>{user.id}</code>\n"
        f"𝗔𝗰𝗰𝗲𝘀𝘀 ➛ <b>{access_str}</b>\n"
        f"𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛ <b>{credits_str}</b>\n"
        f"𝗝𝗼𝗶𝗻𝗲𝗱 ➛ <b>{joined_str}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"𝗗𝗲𝘃 ➛ {dl}"
    )

def _loading_caption(user) -> str:
    ul = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    dl = f'<a href="https://t.me/{DEV_USERNAME}">@{DEV_USERNAME}</a>'
    return (
        f"𝗨𝘀𝗲𝗿 ➛ {ul}\n"
        f"𝗨𝘀𝗲𝗿 𝗜𝗗 ➛ <code>{user.id}</code>\n"
        f"𝗔𝗰𝗰𝗲𝘀𝘀 ➛ <b>Loading…</b>\n"
        f"𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛ <b>Loading…</b>\n"
        f"𝗝𝗼𝗶𝗻𝗲𝗱 ➛ <b>Loading…</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"𝗗𝗲𝘃 ➛ {dl}"
    )

def mask_receipt_id(receipt_id):
    parts = receipt_id.split('-')
    if len(parts) == 3:
        m = parts[1]
        if len(m) >= 2:
            return f"{parts[0]}-{m[:2]}XX{m[4:]}-{parts[2]}"
    return receipt_id

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KEYBOARDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MAIN_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💳 𝗖𝗵𝗲𝗰𝗸𝗲𝗿", callback_data="menu_gates"),
     InlineKeyboardButton(text="🛠️ 𝗧𝗼𝗼𝗹𝘀", callback_data="menu_tools")],
    [InlineKeyboardButton(text="👤 𝗠𝘆 𝗔𝗰𝗰𝗼𝘂𝗻𝘁", callback_data="menu_account"),
     InlineKeyboardButton(text="💎 𝗕𝘂𝘆 𝗡𝗼𝘄", callback_data="menu_pricing")],
    [InlineKeyboardButton(text="📢 𝗨𝗽𝗱𝗮𝘁𝗲𝘀", url=CHANNEL_LINK),
     InlineKeyboardButton(text="💬 𝗚𝗿𝗼𝘂𝗽", url=GROUP_LINK)],
    [InlineKeyboardButton(text="🆘 𝗦𝘂𝗽𝗽𝗼𝗿𝘁", url=f"https://t.me/{DEV_USERNAME}")]
])

def _back(target):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data=target)]])

_KB_BACK_MAIN = _back("back_main")
_KB_BACK_GATES = _back("menu_gates")
_KB_BACK_MASS = _back("menu_mass_in_gates")
_KB_BACK_AUTH = _back("menu_auth")
_KB_BACK_CHARGE = _back("menu_charge")
_KB_BACK_AUTO = _back("menu_auto")
_KB_BACK_TOOLS = _back("menu_tools")
_KB_BACK_ACCOUNT = _back("menu_account")

_KB_PRICING = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 𝗣𝗮𝘆 𝗩𝗶𝗮", callback_data="menu_payment_methods")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="back_main")]
])

_KB_GATES = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔐 𝗔𝘂𝘁𝗵", callback_data="menu_auth"),
     InlineKeyboardButton(text="💳 𝗖𝗵𝗮𝗿𝗴𝗲", callback_data="menu_charge")],
    [InlineKeyboardButton(text="📦 𝗠𝗮𝘀𝘀", callback_data="menu_mass_in_gates"),
     InlineKeyboardButton(text="⚡ 𝗔𝘂𝘁𝗼 𝗛𝗶𝘁𝘁𝗲𝗿", callback_data="menu_auto")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="back_main")]
])

_KB_AUTH = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲", callback_data="info_auth_stripe"),
     InlineKeyboardButton(text="𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲", callback_data="info_auth_braintree")],
    [InlineKeyboardButton(text="𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝗩𝗕𝗩", callback_data="info_auth_braintree_vbv"),
     InlineKeyboardButton(text="𝗠𝗔𝗨 𝗦𝘁𝗿𝗶𝗽𝗲", callback_data="info_auth_mau")],
    [InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲 𝗟𝗶𝗻𝗸", callback_data="info_auth_striplink")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="menu_gates")]
])

_KB_CHARGE = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲", callback_data="info_charge_stripe"),
     InlineKeyboardButton(text="𝗣𝗮𝘆𝗽𝗮𝗹", callback_data="info_charge_paypal")],
    [InlineKeyboardButton(text="𝗦𝗵𝗼𝗽𝗶𝗳𝘆", callback_data="info_charge_shopify"),
     InlineKeyboardButton(text="𝗣𝗮𝘆𝗙𝗮𝘀𝘁", callback_data="info_charge_payfast")],
    [InlineKeyboardButton(text="𝗙𝗮𝘁𝗭𝗲𝗯𝗿𝗮", callback_data="info_charge_fatzebra"),
     InlineKeyboardButton(text="𝗡𝗠𝗜", callback_data="info_charge_nmi")],
    [InlineKeyboardButton(text="𝗕𝗹𝘂𝗲𝗽𝗮𝘆", callback_data="info_charge_bluepay"),
     InlineKeyboardButton(text="𝗔𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲.𝗻𝗲𝘁", callback_data="info_charge_authnet")],
    [InlineKeyboardButton(text="𝗣𝗮𝘆𝗪𝗮𝘆", callback_data="info_charge_payway"),
     InlineKeyboardButton(text="𝗥𝗮𝘇𝗼𝗿𝗽𝗮𝘆", callback_data="info_charge_razorpay")],
    [InlineKeyboardButton(text="𝗣𝗮𝘆𝗨", callback_data="info_charge_payu"),
     InlineKeyboardButton(text="𝗥𝗲𝗰𝘂𝗿𝗹𝘆", callback_data="info_charge_recurly")],
    [InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲 𝟭$", callback_data="info_charge_stripe1")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="menu_gates")]
])

_KB_MASS = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="𝗦𝗵𝗼𝗽𝗶𝗳𝘆", callback_data="info_msh_gate"),
     InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲", callback_data="info_mst_gate")],
    [InlineKeyboardButton(text="𝗠𝗔𝗨 𝗦𝘁𝗿𝗶𝗽𝗲", callback_data="info_mau_gate"),
     InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲 𝗟𝗶𝗻𝗸", callback_data="info_msl_gate")],
    [InlineKeyboardButton(text="𝗕𝗹𝘂𝗲𝗣𝗮𝘆", callback_data="info_mbp_gate"),
     InlineKeyboardButton(text="𝗥𝗲𝗰𝘂𝗿𝗹𝘆", callback_data="info_mrc_gate")],
    [InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲 𝟭$", callback_data="info_ms1_gate")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="menu_gates")]
])

_KB_AUTO = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚡ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗛𝗶𝘁𝘁𝗲𝗿", callback_data="info_stco_gate")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="menu_gates")]
])

_KB_TOOLS = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎭 𝗙𝗮𝗸𝗲 𝗚𝗲𝗻", callback_data="info_fake"),
     InlineKeyboardButton(text="💳 𝗚𝗲𝗻 𝗖𝗮𝗿𝗱", callback_data="info_gen")],
    [InlineKeyboardButton(text="🔍 𝗕𝗜𝗡 𝗟𝗼𝗼𝗸𝘂𝗽", callback_data="info_bin")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="back_main")]
])

_KB_ACCOUNT = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 𝗠𝘆 𝗦𝘁𝗮𝘁𝘀", callback_data="info_my_stats"),
     InlineKeyboardButton(text="💎 𝗨𝗽𝗴𝗿𝗮𝗱𝗲", callback_data="menu_pricing")],
    [InlineKeyboardButton(text="📜 𝗛𝗶𝘀𝘁𝗼𝗿𝘆", callback_data="info_history")],
    [InlineKeyboardButton(text="« 𝗕𝗮𝗰𝗸", callback_data="back_main")]
])

_SEP = "━━━━━━━━━━━━━━━━"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATIC MENU MAP (continued)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_PAYMENT_SELECT_TEXT = "<b>✨ 𝗦𝗲𝗹𝗲𝗰𝘁 𝗬𝗼𝘂𝗿 𝗣𝗹𝗮𝗻 ✨\n\nChoose a plan to proceed with\nsecure crypto payment</b>"

STATIC_MENU_MAP: dict = {
    "menu_pricing": (PRICING_TEXT, _KB_PRICING),
    
    "menu_gates": (
        f"<b>🔐 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 𝗦𝘆𝘀𝘁𝗲𝗺</b>\n\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘀:</b>\n"
        f"┣ 𝗔𝘂𝘁𝗵 𝗚𝗮𝘁𝗲𝘀 ➛ <b>5</b> ✅\n"
        f"┣ 𝗖𝗵𝗮𝗿𝗴𝗲 𝗚𝗮𝘁𝗲𝘀 ➛ <b>13</b> ✅\n"
        f"┣ 𝗠𝗮𝘀𝘀 𝗚𝗮𝘁𝗲𝘀 ➛ <b>7</b> ✅\n"
        f"┗ 𝗔𝘂𝘁𝗼 𝗛𝗶𝘁𝘁𝗲𝗿𝘀 ➛ <b>1</b> ✅\n"
        f"{_SEP}\n"
        f"<i>Select a category below</i>",
        _KB_GATES
    ),
    
    "menu_mass_in_gates": (
        f"<b>📦 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸𝗲𝗿</b>\n\n"
        f"<b>📌 𝗟𝗶𝗺𝗶𝘁𝘀:</b>\n"
        f"┣ 𝗙𝗿𝗲𝗲 ➛ <b>10</b> 𝗰𝗮𝗿𝗱𝘀\n"
        f"┗ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 ➛ <b>𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱</b>\n"
        f"{_SEP}\n"
        f"<i>Select a mass gate</i>",
        _KB_MASS
    ),
    
    "menu_auth": (
        f"<b>🔐 𝗔𝘂𝘁𝗵 𝗚𝗮𝘁𝗲𝘀</b>\n\n"
        f"<b>Available:</b>\n"
        f"┣ 𝗦𝘁𝗿𝗶𝗽𝗲 𝟬$ ➛ <code>/chk</code>\n"
        f"┣ 𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝟬$ ➛ <code>/b3</code>\n"
        f"┣ 𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝗩𝗕𝗩 ➛ <code>/vbv</code>\n"
        f"┣ 𝗠𝗔𝗨 𝗦𝘁𝗿𝗶𝗽𝗲 ➛ <code>/au</code> 🆕\n"
        f"┗ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗟𝗶𝗻𝗸 ➛ <code>/sl</code> 🆕\n"
        f"{_SEP}\n"
        f"<i>Select a gate for more info</i>",
        _KB_AUTH
    ),
    
    "menu_charge": (
        f"<b>💳 𝗖𝗵𝗮𝗿𝗴𝗲 𝗚𝗮𝘁𝗲𝘀</b>\n\n"
        f"<b>Available:</b>\n"
        f"┣ 𝗦𝘁𝗿𝗶𝗽𝗲 𝟭$ ➛ <code>/st</code>\n"
        f"┣ 𝗣𝗮𝘆𝗽𝗮𝗹 𝟬.𝟭𝟬$ ➛ <code>/pp</code>\n"
        f"┣ 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝟱$ ➛ <code>/hc</code>\n"
        f"┣ 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝟭$ ➛ <code>/sp</code>\n"
        f"┣ 𝗣𝗮𝘆𝗙𝗮𝘀𝘁 𝟬.𝟯𝟬$ ➛ <code>/pf</code>\n"
        f"┣ 𝗙𝗮𝘁𝗭𝗲𝗯𝗿𝗮 𝟰$ ➛ <code>/ft</code>\n"
        f"┣ 𝗡𝗠𝗜 𝟭$ ➛ <code>/nmi</code>\n"
        f"┣ 𝗡𝗠𝗜𝟮 𝟭$ ➛ <code>/nmi2</code>\n"
        f"┣ 𝗕𝗹𝘂𝗲𝗣𝗮𝘆 𝟮𝟬$ ➛ <code>/bl</code>\n"
        f"┣ 𝗔𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲.𝗻𝗲𝘁 𝟭$ ➛ <code>/at</code>\n"
        f"┣ 𝗣𝗮𝘆𝗪𝗮𝘆 𝟭$ ➛ <code>/pw</code>\n"
        f"┣ 𝗥𝗮𝘇𝗼𝗿𝗽𝗮𝘆 𝟭₹ ➛ <code>/rz</code>\n"
        f"┣ 𝗣𝗮𝘆𝗨 𝟭$ ➛ <code>/pyu</code>\n"
        f"┣ 𝗥𝗲𝗰𝘂𝗿𝗹𝘆 ➛ <code>/rc</code> 🆕\n"
        f"┗ 𝗦𝘁𝗿𝗶𝗽𝗲 𝟭$ (𝗠𝗮𝗿𝗶𝗻𝗲𝗿𝘀) ➛ <code>/s1</code> 🆕\n"
        f"{_SEP}\n"
        f"<i>Select a gate for more info</i>",
        _KB_CHARGE
    ),
    
    "menu_auto": (
        f"<b>⚡ 𝗔𝘂𝘁𝗼 𝗛𝗶𝘁𝘁𝗲𝗿𝘀</b>\n\n"
        f"<b>Available:</b>\n"
        f"┗ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗼 𝗛𝗶𝘁𝘁𝗲𝗿 ➛ <code>/stco</code>\n"
        f"{_SEP}\n"
        f"<i>Auto-hitter runs continuously</i>",
        _KB_AUTO
    ),
    
    "menu_tools": (
        f"<b>🛠️ 𝗧𝗼𝗼𝗹𝗯𝗼𝘅</b>\n\n"
        f"<b>Available Tools:</b>\n"
        f"┣ 🎭 𝗙𝗮𝗸𝗲 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗼𝗿 ➛ <code>/fake</code>\n"
        f"┣ 💳 𝗖𝗮𝗿𝗱 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗼𝗿 ➛ <code>/gen</code>\n"
        f"┗ 🔍 𝗕𝗜𝗡 𝗟𝗼𝗼𝗸𝘂𝗽 ➛ <code>/bin</code>\n"
        f"{_SEP}\n"
        f"<i>Select a tool</i>",
        _KB_TOOLS
    ),
    
    "menu_account": (
        f"<b>👤 𝗠𝘆 𝗔𝗰𝗰𝗼𝘂𝗻𝘁</b>\n\n"
        f"<b>Options:</b>\n"
        f"┣ 📊 𝗩𝗶𝗲𝘄 𝗦𝘁𝗮𝘁𝘀\n"
        f"┣ 💎 𝗨𝗽𝗴𝗿𝗮𝗱𝗲 𝗣𝗹𝗮𝗻\n"
        f"┗ 📜 𝗩𝗶𝗲𝘄 𝗛𝗶𝘀𝘁𝗼𝗿𝘆\n"
        f"{_SEP}\n"
        f"<i>Manage your account</i>",
        _KB_ACCOUNT
    ),

    "info_auth_stripe": (
        f"{_SEP}\n"
        f"<b>🔐 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/chk</code>\n"
        f"<b>📦 𝗠𝗮𝘀𝘀 ➛</b> <code>/mchk</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟭𝟲\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗔𝘂𝘁𝗵\n"
        f"{_SEP}", _KB_BACK_AUTH),
    
    "info_auth_braintree": (
        f"{_SEP}\n"
        f"<b>🔐 𝗚𝗮𝘁𝗲 ➛ 𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝗔𝘂𝘁𝗵</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/b3</code>\n"
        f"<b>📦 𝗠𝗮𝘀𝘀 ➛</b> <code>/mb3</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟮\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗔𝘂𝘁𝗵\n"
        f"{_SEP}", _KB_BACK_AUTH),
    
    "info_auth_braintree_vbv": (
        f"{_SEP}\n"
        f"<b>🔐 𝗚𝗮𝘁𝗲 ➛ 𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝗩𝗕𝗩</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/vbv</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟭\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗔𝘂𝘁𝗵\n"
        f"{_SEP}", _KB_BACK_AUTH),
    
    "info_auth_mau": (
        f"{_SEP}\n"
        f"<b>🔐 𝗚𝗮𝘁𝗲 ➛ 𝗠𝗔𝗨 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵</b> 🆕\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/au</code>\n"
        f"<b>📦 𝗠𝗮𝘀𝘀 ➛</b> <code>/mau</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗔𝘂𝘁𝗵\n"
        f"{_SEP}", _KB_BACK_AUTH),
    
    "info_auth_striplink": (
        f"{_SEP}\n"
        f"<b>🔐 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗟𝗶𝗻𝗸</b> 🆕\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/sl</code>\n"
        f"<b>📦 𝗠𝗮𝘀𝘀 ➛</b> <code>/msl</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗔𝘂𝘁𝗵\n"
        f"{_SEP}", _KB_BACK_AUTH),

    # ─── CHARGE INFO ──────────────────────────────────────
    
    "info_charge_stripe": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗖𝗵𝗮𝗿𝗴𝗲</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/st</code>\n"
        f"<b>📦 𝗠𝗮𝘀𝘀 ➛</b> <code>/mst</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟰\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_paypal": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗣𝗮𝘆𝗣𝗮𝗹</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬.𝟭𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/pp</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟳\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_shopify": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝟱$</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟱$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/hc</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝟭$</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/sp</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_payfast": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗣𝗮𝘆𝗙𝗮𝘀𝘁</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬.𝟯𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/pf</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟭\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_fatzebra": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗙𝗮𝘁𝗭𝗲𝗯𝗿𝗮</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟰$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/ft</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟭\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_nmi": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗡𝗠𝗜</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/nmi</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗡𝗠𝗜𝟮</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/nmi2</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_bluepay": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗕𝗹𝘂𝗲𝗣𝗮𝘆</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟮𝟬$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/bl</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟭\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_authnet": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗔𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲.𝗻𝗲𝘁</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/at</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_payway": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗣𝗮𝘆𝗪𝗮𝘆</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/pw</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_razorpay": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗥𝗮𝘇𝗼𝗿𝗽𝗮𝘆</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭₹\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/rz</code>\n"
        f"<b>🌐 𝗦𝗶𝘁𝗲𝘀 ➛</b> 𝟱\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_payu": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗣𝗮𝘆𝗨</b>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/pyu</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_recurly": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗥𝗲𝗰𝘂𝗿𝗹𝘆</b> 🆕\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/rc</code>\n"
        f"<b>📦 𝗠𝗮𝘀𝘀 ➛</b> <code>/mrc</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),
    
    "info_charge_stripe1": (
        f"{_SEP}\n"
        f"<b>💳 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝟭$ (𝗠𝗮𝗿𝗶𝗻𝗲𝗿𝘀)</b> 🆕\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/s1</code>\n"
        f"<b>📦 𝗠𝗮𝘀𝘀 ➛</b> <code>/ms1</code>\n"
        f"<b>📊 𝗦𝘁𝗮𝘁𝘂𝘀 ➛</b> ✅ 𝗟𝗶𝘃𝗲\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗖𝗵𝗮𝗿𝗴𝗲\n"
        f"{_SEP}", _KB_BACK_CHARGE),

    # ─── MASS INFO ────────────────────────────────────────
    
    "info_msh_gate": (
        f"{_SEP}\n"
        f"<b>📦 𝗚𝗮𝘁𝗲 ➛ 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗠𝗮𝘀𝘀</b>\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/msh</code>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟬-𝟮𝟬$\n"
        f"<b>📊 𝗟𝗶𝗺𝗶𝘁 ➛</b> 𝗙𝗿𝗲𝗲: 𝟭𝟬 | 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗠𝗮𝘀𝘀\n"
        f"{_SEP}", _KB_BACK_MASS),
    
    "info_mst_gate": (
        f"{_SEP}\n"
        f"<b>📦 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗠𝗮𝘀𝘀</b>\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/mst</code>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📊 𝗟𝗶𝗺𝗶𝘁 ➛</b> 𝗙𝗿𝗲𝗲: 𝟭𝟬 | 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗠𝗮𝘀𝘀\n"
        f"{_SEP}", _KB_BACK_MASS),
    
    "info_mau_gate": (
        f"{_SEP}\n"
        f"<b>📦 𝗚𝗮𝘁𝗲 ➛ 𝗠𝗔𝗨 𝗦𝘁𝗿𝗶𝗽𝗲 𝗠𝗮𝘀𝘀</b> 🆕\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/mau</code>\n"
        f"<b>📊 𝗟𝗶𝗺𝗶𝘁 ➛</b> 𝗙𝗿𝗲𝗲: 𝟭𝟬 | 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗠𝗮𝘀𝘀\n"
        f"{_SEP}", _KB_BACK_MASS),
    
    "info_msl_gate": (
        f"{_SEP}\n"
        f"<b>📦 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗟𝗶𝗻𝗸 𝗠𝗮𝘀𝘀</b> 🆕\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/msl</code>\n"
        f"<b>📊 𝗟𝗶𝗺𝗶𝘁 ➛</b> 𝗙𝗿𝗲𝗲: 𝟭𝟬 | 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗠𝗮𝘀𝘀\n"
        f"{_SEP}", _KB_BACK_MASS),
    
    "info_mbp_gate": (
        f"{_SEP}\n"
        f"<b>📦 𝗚𝗮𝘁𝗲 ➛ 𝗕𝗹𝘂𝗲𝗣𝗮𝘆 𝗠𝗮𝘀𝘀</b> 🆕\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/mbp</code>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟮𝟬$\n"
        f"<b>📊 𝗟𝗶𝗺𝗶𝘁 ➛</b> 𝗙𝗿𝗲𝗲: 𝟭𝟬 | 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗠𝗮𝘀𝘀\n"
        f"{_SEP}", _KB_BACK_MASS),
    
    "info_mrc_gate": (
        f"{_SEP}\n"
        f"<b>📦 𝗚𝗮𝘁𝗲 ➛ 𝗥𝗲𝗰𝘂𝗿𝗹𝘆 𝗠𝗮𝘀𝘀</b> 🆕\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/mrc</code>\n"
        f"<b>📊 𝗟𝗶𝗺𝗶𝘁 ➛</b> 𝗙𝗿𝗲𝗲: 𝟭𝟬 | 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗠𝗮𝘀𝘀\n"
        f"{_SEP}", _KB_BACK_MASS),
    
    "info_ms1_gate": (
        f"{_SEP}\n"
        f"<b>📦 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝟭$ 𝗠𝗮𝘀𝘀</b> 🆕\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/ms1</code>\n"
        f"<b>💰 𝗖𝗼𝘀𝘁 ➛</b> 𝟭$\n"
        f"<b>📊 𝗟𝗶𝗺𝗶𝘁 ➛</b> 𝗙𝗿𝗲𝗲: 𝟭𝟬 | 𝗣𝗿𝗲𝗺𝗶𝘂𝗺: 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"<b>🏷️ 𝗧𝘆𝗽𝗲 ➛</b> 𝗠𝗮𝘀𝘀\n"
        f"{_SEP}", _KB_BACK_MASS),
    
    "info_stco_gate": (
        f"{_SEP}\n"
        f"<b>⚡ 𝗚𝗮𝘁𝗲 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗼 𝗛𝗶𝘁𝘁𝗲𝗿</b>\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/stco</code>\n"
        f"<b>📊 𝗧𝘆𝗽𝗲 ➛</b> 𝗔𝘂𝘁𝗼 𝗛𝗶𝘁𝘁𝗲𝗿\n"
        f"<b>🛑 𝗦𝘁𝗼𝗽 ➛</b> 🛑 𝗕𝘂𝘁𝘁𝗼𝗻\n"
        f"{_SEP}", _KB_BACK_AUTO),

    # ─── TOOLS INFO ───────────────────────────────────────
    
    "info_fake": (
        f"{_SEP}\n"
        f"<b>🎭 𝗧𝗼𝗼𝗹 ➛ 𝗙𝗮𝗸𝗲 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗼𝗿</b>\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/fake</code>\n"
        f"<b>📊 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝘀 ➛</b> 𝗡𝗮𝗺𝗲, 𝗔𝗱𝗱𝗿𝗲𝘀𝘀, 𝗘𝗺𝗮𝗶𝗹, 𝗣𝗵𝗼𝗻𝗲, 𝗦𝗦𝗡, 𝗗𝗢𝗕\n"
        f"{_SEP}", _KB_BACK_TOOLS),
    
    "info_gen": (
        f"{_SEP}\n"
        f"<b>💳 𝗧𝗼𝗼𝗹 ➛ 𝗖𝗮𝗿𝗱 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗼𝗿</b>\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/gen</code>\n"
        f"<b>📊 𝗨𝘀𝗮𝗴𝗲 ➛</b> <code>/gen [bin]</code>\n"
        f"<b>📊 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝘀 ➛</b> 𝗩𝗮𝗹𝗶𝗱 𝗖𝗿𝗲𝗱𝗶𝘁 𝗖𝗮𝗿𝗱𝘀\n"
        f"{_SEP}", _KB_BACK_TOOLS),
    
    "info_bin": (
        f"{_SEP}\n"
        f"<b>🔍 𝗧𝗼𝗼𝗹 ➛ 𝗕𝗜𝗡 𝗟𝗼𝗼𝗸𝘂𝗽</b>\n"
        f"<b>📟 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 ➛</b> <code>/bin</code>\n"
        f"<b>📊 𝗨𝘀𝗮𝗴𝗲 ➛</b> <code>/bin 411111</code>\n"
        f"<b>📊 𝗦𝗵𝗼𝘄𝘀 ➛</b> 𝗕𝗮𝗻𝗸, 𝗕𝗿𝗮𝗻𝗱, 𝗖𝗼𝘂𝗻𝘁𝗿𝘆, 𝗧𝘆𝗽𝗲\n"
        f"{_SEP}", _KB_BACK_TOOLS),
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _edit(msg: types.Message, text: str, kb: InlineKeyboardMarkup):
    try:
        if msg.caption is not None:
            await msg.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await msg.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    except TypeError:
        pass
    except Exception as e:
        if "Message is not modified" not in str(e):
            logging.warning(f"_edit: {e}")

async def _safe_answer(cb: types.CallbackQuery, text: str = "", **kw):
    try:
        await cb.answer(text, **kw)
    except Exception:
        pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /start
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.message(Command("start"))
async def start(message: types.Message):
    user = message.from_user
    asyncio.create_task(ensure_user_and_credits(user.id, user.username))

    if message.text and len(message.text.split()) > 1 and message.text.split()[1] == "buy":
        await buy_command(message)
        return

    quick = _loading_caption(user)
    caption_task = asyncio.create_task(_get_caption(user))

    sent = await message.reply_photo(photo=START_IMAGE_URL, caption=quick, reply_markup=_MAIN_KB)

    try:
        full = await caption_task
        await sent.edit_caption(caption=full, reply_markup=_MAIN_KB)
    except Exception:
        pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DOT COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOT_COMMAND_MAP = {
    "chk": chk_command, "st": st_command, "sh": sh_command,
    "sp": sp_command, "hc": hc_command, "pf": pf_command,
    "vbv": vbv_command, "ft": ft_command, "bl": bl_command,
    "pp": pp_command, "at": at_command, "pw": pw_command,
    "rz": rz_command, "pyu": pyu_command, "b3": b3_command,
    "nmi": nmi_command, "nmi2": nmi2_command, "stco": stco_command,
    "mst": mst_command, "mau": mau_command, "msl": msl_command,
    "mbp": mbp_command, "mrc": mrc_command, "ms1": ms1_command,
    "bin": binn_command, "binn": binn_command,
    "fake": fake_command, "gen": gen_command,
    "sub": sub_command, "rc": rc_command, "suball": suball_command,
    "g_code": g_code_command, "claim": claim_command, "info": info_command,
    "rsub": rsub_command, "buy": buy_command, "adcr": adcr_command,
    "on": on_command, "off": off_command, "stats": stats_command,
    "proxy": proxy_command, "checkproxy": checkproxy_command,
    "clearproxy": clearproxy_command, "sitechk": sitechk_command,
    "addsite": addsite_command, "siteall": siteall_command,
    "removeall": removeall_command, "dedupe": dedupe_command,
    "proxyinfo": proxyinfo_command, "resetproxy": resetproxy_command,
    "cmds": cmds_command, "fb": feedback_cmd, "broad": broad_command,
    "ban": ban_command, "unban": unban_command, "vps": vps_command,
}

@router.message(F.text.regexp(r'^\.\w+'))
async def dot_command_handler(message: types.Message):
    cmd = message.text.strip().split()[0][1:].lower()
    h = DOT_COMMAND_MAP.get(cmd)
    if h:
        await h(message)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALLBACK HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MASS_PREFIXES = ("mshs_", "mshr_", "msts_", "mstr_", "stco_", "fb_", "cmds_")

@router.callback_query()
async def button_handler(callback: types.CallbackQuery):
    data = callback.data or ""

    if data.startswith(_MASS_PREFIXES):
        return

    msg = callback.message
    if not isinstance(msg, types.Message):
        await _safe_answer(callback, "❌ Message expired. Please use /start again.", show_alert=True)
        return

    user_id = callback.from_user.id

    static = STATIC_MENU_MAP.get(data)
    if static is not None:
        text, kb = static
        if kb is None:
            kb = pay_sys.get_plan_selection_keyboard()
        asyncio.create_task(_safe_answer(callback))
        asyncio.create_task(_edit(msg, text, kb))
        return

    if data == "back_main":
        user = callback.from_user
        quick = _loading_caption(user)
        caption_task = asyncio.create_task(_get_caption(user))
        asyncio.create_task(_safe_answer(callback))
        try:
            if msg.caption is not None:
                await msg.edit_caption(caption=quick, reply_markup=_MAIN_KB, parse_mode="HTML")
            else:
                await msg.answer_photo(photo=START_IMAGE_URL, caption=quick, reply_markup=_MAIN_KB, parse_mode="HTML")
        except TypeError:
            pass
        except Exception as e:
            if "Message is not modified" not in str(e):
                logging.warning(f"back_main load: {e}")
        try:
            full = await caption_task
            await msg.edit_caption(caption=full, reply_markup=_MAIN_KB, parse_mode="HTML")
        except TypeError:
            pass
        except Exception:
            pass
        return

    if data == "show_buy_plans":
        buy_url_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="💎 𝗧𝗮𝗽 𝗛𝗲𝗿𝗲 𝘁𝗼 𝗕𝘂𝘆", url=f"{BOT_LINK}?start=buy")
        ]])
        asyncio.create_task(_safe_answer(callback))
        asyncio.create_task(msg.edit_reply_markup(reply_markup=buy_url_kb))
        return

    if data.startswith("pay_plan_"):
        plan = data[9:]
        if plan not in pay_sys.PLANS:
            asyncio.create_task(_safe_answer(callback))
            asyncio.create_task(msg.answer("Invalid plan!"))
            return
        pi = pay_sys.PLANS[plan]
        pay_sys.set_user_session(user_id, plan)
        text = (
            f"<b>{pi['display']} 𝗣𝗹𝗮𝗻</b>\n"
            f"<b>𝗣𝗿𝗶𝗰𝗲 ➛</b> ${pi['price']}\n"
            f"<b>𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 ➛</b> {pi['days']} Days\n"
            f"<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 ➛</b> {pi['credits']:,}\n"
            f"<b>𝗦𝗲𝗹𝗲𝗰𝘁 𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗠𝗲𝘁𝗵𝗼𝗱:</b>"
        )
        asyncio.create_task(_safe_answer(callback))
        asyncio.create_task(_edit(msg, text, pay_sys.get_network_selection_keyboard(user_id)))
        return

    if data.startswith("pay_back_plans_"):
        try:
            owner_id = int(data[15:])
        except ValueError:
            await _safe_answer(callback, "❌ Error", show_alert=True)
            return
        if user_id != owner_id:
            await _safe_answer(callback, "❌ No permission", show_alert=True)
            return
        asyncio.create_task(_safe_answer(callback))
        asyncio.create_task(_edit(msg, _PAYMENT_SELECT_TEXT, pay_sys.get_plan_selection_keyboard()))
        return

    if data.startswith("pay_direct_"):
        net_key = data[11:]
        session = pay_sys.get_user_session(user_id)
        if not session or not session.get("plan"):
            asyncio.create_task(_safe_answer(callback))
            asyncio.create_task(msg.answer("Session expired!"))
            return
        plan = session["plan"]
        net_info = pay_sys.DIRECT_NETWORKS.get(net_key)
        if not net_info:
            asyncio.create_task(_safe_answer(callback))
            asyncio.create_task(msg.answer("Invalid network!"))
            return
        pay_sys.cancel_user_active_payment(user_id)
        payment_data = await asyncio.to_thread(
            pay_sys.create_payment, user_id, plan, net_info["currency"], net_info["network"]
        )
        if not payment_data:
            await asyncio.gather(
                _safe_answer(callback),
                _edit(msg, "❌ <b>Payment Failed</b>\n\nPlease try again later.",
                      _back("menu_pricing")),
            )
            return
        track_id = payment_data["track_id"]
        pay_sys.register_payment(track_id, user_id, plan)
        caption = pay_sys.format_payment_caption(payment_data, plan)
        kb = pay_sys.get_paid_button_keyboard(track_id, user_id)
        await _safe_answer(callback)
        try:
            sent_msg = await msg.answer(text=caption, reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            logging.error(f"pay_direct send: {e}")
            return
        try:
            await msg.delete()
        except Exception:
            pass
        if sent_msg:
            pay_sys.active_payments[track_id].update({
                "chat_id": sent_msg.chat.id,
                "message_id": sent_msg.message_id,
                "original_text": caption,
            })
        return

    if data.startswith("pay_check_"):
        track_id = data[10:]
        payment = pay_sys.active_payments.get(track_id)
        if not payment or payment.get("user_id") != user_id:
            await _safe_answer(callback, "❌ No permission", show_alert=True)
            return
        bot_i = pay_sys.get_bot()
        if not bot_i:
            await _safe_answer(callback, "❌ Bot error", show_alert=True)
            return
        try:
            status = await asyncio.to_thread(pay_sys.check_payment_status, track_id)
            logging.info(f"pay_check {track_id}: {status}")
            if status and status.lower() == "paid":
                await asyncio.to_thread(pay_sys.activate_plan, user_id, payment["plan"])
                receipt = pay_sys.get_receipt_for_user(user_id, payment["plan"])
                pi = pay_sys.PLANS.get(payment["plan"], {})
                dn = callback.from_user.first_name or callback.from_user.username or "User"
                ul = f'<a href="tg://user?id={user_id}">{dn}</a>'
                mid = mask_receipt_id(receipt['receipt_id']) if receipt else "N/A"
                log_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="💎 𝗕𝘂𝘆 𝗡𝗼𝘄", url=f"{BOT_LINK}?start=buy")
                ]])
                try:
                    await bot_i.send_message(
                        chat_id=LOG_CHANNEL_ID, parse_mode="HTML", reply_markup=log_kb,
                        text=(f"<b>NEW PLAN PURCHASED 🛒</b>\n<b>User ➛</b> {ul}\n"
                              f"<b>Access ➛</b> <b>{pi.get('display','')}</b>\n"
                              f"<b>Amount ➛</b> <b>{pi.get('price',0)} USD</b>\n"
                              f"<b>Receipt ID ➛</b> <code>{mid}</code>")
                    )
                except Exception as le:
                    logging.error(f"log channel: {le}")
                success = (
                    f"✅ <b>𝗧𝗿𝗮𝗻𝘀𝗮𝗰𝘁𝗶𝗼𝗻 𝗦𝘂𝗰𝗰𝗲𝘀𝘀!</b>\n\n"
                    f" <b>𝗣𝗹𝗮𝗻 ➛</b> {pi.get('display','')}\n"
                    f" <b>𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 ➛</b> {pi.get('days',0)} Days\n"
                    f" <b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀 𝗔𝗱𝗱𝗲𝗱 ➛</b> +{pi.get('credits',0):,}\n\n"
                    f" <b>𝗬𝗼𝘂𝗿 𝗣𝗹𝗮𝗻 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗮𝗰𝘁𝗶𝘃𝗮𝘁𝗲𝗱!</b>"
                )
                dm_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🆘 𝗦𝘂𝗽𝗽𝗼𝗿𝘁", url=f"https://t.me/{DEV_USERNAME}")
                ]])
                if receipt:
                    dm = (f"𝐂𝐨𝐧𝐠𝐫𝐚𝐭𝐮𝐥𝐚𝐭𝐢𝐨𝐧𝐬! 🎉 𝐘𝐨𝐮𝐫 𝐚𝐜𝐜𝐞𝐬𝐬 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞𝐝.\n"
                          f"𝗨𝘀𝗲𝗿 ➛ {ul}\n𝗔𝗰𝗰𝗲𝘀𝘀 ➛ <b>{receipt['plan_name']}</b>\n"
                          f"𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 ➛ {receipt['days']} Days\n"
                          f"𝗖𝗿𝗲𝗱𝗶𝘁𝘀 𝗔𝗱𝗱𝗲𝗱 ➛ +{receipt['credits']:,}\n"
                          f"𝗥𝗲𝗰𝗲𝗶𝗽𝘁 𝗜𝗗 ➛ <code>{receipt['receipt_id']}</code>\n"
                          f"𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗮𝘃𝗲 𝘁𝗵𝗶𝘀 𝗿𝗲𝗰𝗲𝗶𝗽𝘁 𝗜𝗗.")
                else:
                    dm = (f"𝐂𝐨𝐧𝐠𝐫𝐚𝐭𝐮𝐥𝐚𝐭𝐢𝐨𝐧𝐬! 🎉 𝐘𝐨𝐮𝐫 𝐚𝐜𝐜𝐞𝐬𝐬 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞𝐝.\n"
                          f"𝗔𝗰𝗰𝗲𝘀𝘀 ➛ <b>{pi.get('display','')}</b>\n"
                          f"𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 ➛ {pi.get('days',0)} Days\n"
                          f"𝗖𝗿𝗲𝗱𝗶𝘁𝘀 𝗔𝗱𝗱𝗲𝗱 ➛ +{pi.get('credits',0):,}\n"
                          f"𝗬𝗼𝘂𝗿 𝗽𝗹𝗮𝗻 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗮𝗰𝘁𝗶𝘃𝗮𝘁𝗲𝗱!")
                await asyncio.gather(
                    _safe_answer(callback, "✅ Payment Confirmed! Plan activated.", show_alert=True),
                    bot_i.edit_message_text(chat_id=payment["chat_id"],
                                            message_id=payment["message_id"], text=success),
                    bot_i.send_message(chat_id=user_id, text=dm, parse_mode="HTML", reply_markup=dm_kb),
                )
                pay_sys._cleanup_payment(track_id, user_id)

            elif status and status.lower() == "expired":
                await asyncio.gather(
                    _safe_answer(callback, "⏰ Payment Expired!", show_alert=True),
                    bot_i.edit_message_text(
                        chat_id=payment["chat_id"], message_id=payment["message_id"],
                        text="<b>Payment Expired</b>\n\nThe payment window has closed.\nPlease start a new payment."
                    ),
                )
                pay_sys._cleanup_payment(track_id, user_id)

            else:
                await _safe_answer(callback, "⏳ Payment not detected yet.\nEnsure exact amount is sent.", show_alert=True)
                cur_text = payment.get("original_text", "")
                if "Payment not detected yet" not in cur_text:
                    pending = (f"{cur_text}\n\n⏳ <b>Payment not detected yet.</b>\n"
                               f"<i>Ensure exact amount is sent. Click 'Paid' again to recheck.</i>")
                    try:
                        await bot_i.edit_message_text(
                            chat_id=payment["chat_id"], message_id=payment["message_id"],
                            text=pending, reply_markup=pay_sys.get_paid_button_keyboard(track_id, user_id)
                        )
                        payment["original_text"] = pending
                    except Exception as e:
                        if "not modified" not in str(e):
                            logging.error(f"pending edit: {e}")
        except Exception as e:
            logging.error(f"pay_check error: {e}")
            await _safe_answer(callback, "⚠️ Network error. Try again.", show_alert=True)
        return

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXPLICIT CALLBACK REGISTRATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

dp.callback_query.register(sh_callback_handler, F.data.startswith("sh_"))
dp.callback_query.register(stco_callback_handler, F.data.startswith("stco_"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMAND REGISTRATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

for _cmd, _fn in [
    ("pp", pp_command), ("pw", pw_command), ("at", at_command), ("pf", pf_command),
    ("b3", b3_command), ("chk", chk_command), ("sh", sh_command), ("st", st_command),
    ("hc", hc_command), ("sp", sp_command), ("stco", stco_command), ("vbv", vbv_command),
    ("ft", ft_command), ("nmi", nmi_command), ("nmi2", nmi2_command), ("bl", bl_command),
    ("rz", rz_command), ("pyu", pyu_command),
    ("au", au_command), ("sl", sl_command), ("rc", rc_command), ("s1", s1_command),
    ("sub", sub_command), ("rc", rc_command), ("suball", suball_command),
    ("g_code", g_code_command), ("claim", claim_command),
    ("info", info_command), ("rsub", rsub_command), ("buy", buy_command),
    ("adcr", adcr_command), ("on", on_command), ("off", off_command),
    ("mst", mst_command), ("mau", mau_command), ("msl", msl_command),
    ("mbp", mbp_command), ("mrc", mrc_command), ("ms1", ms1_command),
    ("sitechk", sitechk_command), ("addsite", addsite_command),
    ("siteall", siteall_command), ("removeall", removeall_command), ("dedupe", dedupe_command),
    ("proxyinfo", proxyinfo_command), ("resetproxy", resetproxy_command),
    ("stats", stats_command), ("proxy", proxy_command), ("checkproxy", checkproxy_command),
    ("clearproxy", clearproxy_command), ("bin", binn_command), ("binn", binn_command),
    ("fake", fake_command), ("gen", gen_command),
]:
    dp.message.register(_fn, Command(_cmd))

setup_feedback_handler(dp)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POLLING MODE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("🤖 Bot starting with polling...")
    pay_sys.set_bot(bot)
    try:
        dp.run_polling(bot)
    except KeyboardInterrupt:
        print("Bot stopped.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /approve - Admin approve payment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.message(Command("approve"))
async def approve_command(message: types.Message):
    user = message.from_user
    if user.id not in ADMIN_IDS:
        await message.reply("❌ 𝗡𝗼𝘁 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱.")
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "❌ 𝗨𝘀𝗮𝗴𝗲: /approve {user_id} {plan}\n"
            "𝗣𝗹𝗮𝗻𝘀: core, elite, root",
            parse_mode="HTML"
        )
        return
    
    target_id = int(args[0])
    plan = args[1].lower()
    
    if plan not in ["core", "elite", "root"]:
        await message.reply("❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗽𝗹𝗮𝗻. Use: core, elite, root", parse_mode="HTML")
        return
    
    receipt_id = await asyncio.to_thread(pay_sys.activate_plan, target_id, plan)
    if receipt_id:
        pi = pay_sys.PLANS.get(plan, {})
        await message.reply(
            f"✅ 𝗣𝗹𝗮𝗻 𝗮𝗰𝘁𝗶𝘃𝗮𝘁𝗲𝗱!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>𝗨𝘀𝗲𝗿 𝗜𝗗:</b> <code>{target_id}</code>\n"
            f"<b>𝗣𝗹𝗮𝗻:</b> {pi.get('display', plan)}\n"
            f"<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀:</b> +{pi.get('credits', 0):,}\n"
            f"<b>𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻:</b> {pi.get('days', 0)} 𝗗𝗮𝘆𝘀\n"
            f"<b>𝗥𝗲𝗰𝗲𝗶𝗽𝘁:</b> <code>{receipt_id}</code>",
            parse_mode="HTML"
        )
        
        # Notify user
        try:
            await message.bot.send_message(
                chat_id=target_id,
                text=f"✅ 𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱!\n"
                     f"━━━━━━━━━━━━━━━━━━━━━━\n"
                     f"<b>𝗣𝗹𝗮𝗻:</b> {pi.get('display', plan)}\n"
                     f"<b>𝗖𝗿𝗲𝗱𝗶𝘁𝘀:</b> +{pi.get('credits', 0):,}\n"
                     f"<b>𝗥𝗲𝗰𝗲𝗶𝗽𝘁:</b> <code>{receipt_id}</code>\n\n"
                     f"𝗧𝗵𝗮𝗻𝗸 𝘆𝗼𝘂 𝗳𝗼𝗿 𝘆𝗼𝘂𝗿 𝗽𝘂𝗿𝗰𝗵𝗮𝘀𝗲! 🚀",
                parse_mode="HTML"
            )
        except:
            pass
    else:
        await message.reply("❌ 𝗙𝗮𝗶𝗹𝗲𝗱 𝘁𝗼 𝗮𝗰𝘁𝗶𝘃𝗮𝘁𝗲 𝗽𝗹𝗮𝗻.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RATE LIMIT MIDDLEWARE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from aiogram import BaseMiddleware
from typing import Dict, Any, Awaitable, Callable
import asyncio

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.last_message: Dict[int, float] = {}
    
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id if event.from_user else 0
        if user_id:
            now = time.time()
            last = self.last_message.get(user_id, 0)
            elapsed = now - last
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            self.last_message[user_id] = time.time()
        return await handler(event, data)

# Add middleware
dp.message.middleware(RateLimitMiddleware(delay=0.3))
