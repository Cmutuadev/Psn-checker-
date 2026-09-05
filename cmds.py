from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

ENTRIES_PER_PAGE = 5
_SEP = "━━━━━━━━━━━━━━━━"
_SP = "\u00a0"

PAGES = [
    {
        "title": "🔐 Auth Gates",
        "entries": [
            {"gate": "Stripe Auth 0$",      "cmd": "/chk", "limit": None, "premium": False},
            {"gate": "Braintree 0$",        "cmd": "/b3",  "limit": None, "premium": False},
            {"gate": "Braintree VBV 0$",    "cmd": "/vbv", "limit": None, "premium": False},
            {"gate": "MAU Stripe Auth",     "cmd": "/au",  "limit": None, "premium": False},
            {"gate": "Stripe Link",         "cmd": "/sl",  "limit": None, "premium": False},
        ],
    },
    {
        "title": "💳 Charge Gates I",
        "entries": [
            {"gate": "Stripe 1$",           "cmd": "/st",  "limit": None, "premium": False},
            {"gate": "PayPal 0.10$",        "cmd": "/pp",  "limit": None, "premium": False},
            {"gate": "Shopify 5$",          "cmd": "/hc",  "limit": None, "premium": False},
            {"gate": "Shopify 1$",          "cmd": "/sp",  "limit": None, "premium": False},
            {"gate": "PayFast 0.30$",       "cmd": "/pf",  "limit": None, "premium": False},
        ],
    },
    {
        "title": "💳 Charge Gates II",
        "entries": [
            {"gate": "FatZebra 4$",         "cmd": "/ft",  "limit": None, "premium": False},
            {"gate": "NMI 1$",              "cmd": "/nmi", "limit": None, "premium": False},
            {"gate": "NMI2 1$",             "cmd": "/nmi2","limit": None, "premium": False},
            {"gate": "BluePay 20$",         "cmd": "/bl",  "limit": None, "premium": False},
            {"gate": "Authorize.net 1$",    "cmd": "/at",  "limit": None, "premium": False},
        ],
    },
    {
        "title": "💳 Charge Gates III",
        "entries": [
            {"gate": "PayWay 1$",           "cmd": "/pw",  "limit": None, "premium": False},
            {"gate": "Razorpay 1₹",         "cmd": "/rz",  "limit": None, "premium": False},
            {"gate": "PayU 1$",             "cmd": "/pyu", "limit": None, "premium": True},
            {"gate": "Recurly",             "cmd": "/rc",  "limit": None, "premium": False},
            {"gate": "Stripe 1$ (Mariners)","cmd": "/s1",  "limit": None, "premium": False},
        ],
    },
    {
        "title": "📦 Mass Gates",
        "entries": [
            {"gate": "Shopify Mass",        "cmd": "/msh", "limit": "Free: 10 | Premium: Unlimited", "premium": True},
            {"gate": "Stripe Mass",         "cmd": "/mst", "limit": "Free: 10 | Premium: Unlimited", "premium": True},
            {"gate": "MAU Stripe Mass",     "cmd": "/mau", "limit": "Free: 10 | Premium: Unlimited", "premium": True},
            {"gate": "Stripe Link Mass",    "cmd": "/msl", "limit": "Free: 10 | Premium: Unlimited", "premium": True},
            {"gate": "BluePay Mass",        "cmd": "/mbp", "limit": "Free: 10 | Premium: Unlimited", "premium": True},
        ],
    },
    {
        "title": "📦 Mass Gates II",
        "entries": [
            {"gate": "Recurly Mass",        "cmd": "/mrc", "limit": "Free: 10 | Premium: Unlimited", "premium": True},
            {"gate": "Stripe 1$ Mass",      "cmd": "/ms1", "limit": "Free: 10 | Premium: Unlimited", "premium": True},
            {"gate": "Stripe Hitter Auto",  "cmd": "/stco","limit": None, "premium": False},
            {"gate": "Shopify 1$ Single",   "cmd": "/sh",  "limit": "50", "premium": False},
        ],
    },
    {
        "title": "🛠️ Tools",
        "entries": [
            {"gate": "Fake Generator",      "cmd": "/fake",       "limit": None, "premium": False},
            {"gate": "Card Generator",      "cmd": "/gen",        "limit": None, "premium": False},
            {"gate": "BIN Lookup",          "cmd": "/bin",        "limit": None, "premium": False},
            {"gate": "Set Proxy",           "cmd": "/proxy",      "limit": None, "premium": False},
            {"gate": "Check Proxy",         "cmd": "/checkproxy", "limit": None, "premium": False},
        ],
    },
    {
        "title": "👤 Account",
        "entries": [
            {"gate": "My Stats",            "cmd": "/info",   "limit": None, "premium": False},
            {"gate": "Statistics",          "cmd": "/stats",  "limit": None, "premium": False},
            {"gate": "Buy Plan",            "cmd": "/buy",    "limit": None, "premium": False},
            {"gate": "Claim Code",          "cmd": "/claim",  "limit": None, "premium": False},
            {"gate": "Give Feedback",       "cmd": "/fb",     "limit": None, "premium": False},
        ],
    },
]

TOTAL_PAGES = len(PAGES)

def _build_text(i: int) -> str:
    page = PAGES[i]
    lines = [_SEP, f"<b>{page['title']}  ·  {i + 1} / {TOTAL_PAGES}</b>", _SEP]
    for e in page["entries"]:
        lines.append(f"<b>Gate  ➛  {e['gate']}</b>")
        lines.append(f"<b>Cmd   ➛  {e['cmd']}</b>")
        if e["limit"] is not None:
            lines.append(f"<b>Limit ➛  {e['limit']}</b>")
        lines.append(f"<b>Type  ➛  {'Premium' if e['premium'] else 'Free'}</b>")
        lines.append(_SEP)
    pad = ENTRIES_PER_PAGE - len(page["entries"])
    for _ in range(pad):
        lines.append(f"<b>{_SP}</b>")
        lines.append(f"<b>{_SP}</b>")
        lines.append(f"<b>{_SP}</b>")
        lines.append(_SEP)
    return "\n".join(lines)

def _build_kb(i: int) -> InlineKeyboardMarkup:
    nav = []
    if i > 0:
        nav.append(InlineKeyboardButton(text="« Prev", callback_data=f"cmds_page_{i - 1}"))
    nav.append(InlineKeyboardButton(text=f"{i + 1} / {TOTAL_PAGES}", callback_data="cmds_noop"))
    if i < TOTAL_PAGES - 1:
        nav.append(InlineKeyboardButton(text="Next »", callback_data=f"cmds_page_{i + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[nav])

_CACHE: list[tuple[str, InlineKeyboardMarkup]] = [
    (_build_text(i), _build_kb(i)) for i in range(TOTAL_PAGES)
]

@router.message(Command("cmds"))
async def cmds_command(message: types.Message):
    text, kb = _CACHE[0]
    await message.reply(text=text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)

@router.callback_query(F.data.startswith("cmds_page_"))
async def cmds_page_callback(callback: types.CallbackQuery):
    await callback.answer()
    try:
        idx = int(callback.data[10:])
    except ValueError:
        return
    if not (0 <= idx < TOTAL_PAGES):
        return
    text, kb = _CACHE[idx]
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        pass

@router.callback_query(F.data == "cmds_noop")
async def cmds_noop(callback: types.CallbackQuery):
    await callback.answer()