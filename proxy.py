import re
import logging
import aiohttp
import asyncio
from urllib.parse import quote
from pymongo import MongoClient

from aiogram import types, F, Router
from aiogram.types import BufferedInputFile

router = Router()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_CONCURRENT_CHECKS = 5
PROXY_TIMEOUT = 8
IPIFY_API_URL = "https://api.ipify.org?format=json"

MONGO_URI = "mongodb+srv://myproject:myproject@myproject.wqcf3.mongodb.net/?retryWrites=true&w=majority&appName=myproject"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARSING HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def parse_proxy_input(proxy_input):
    s = proxy_input.strip()
    protocol = 'http'
    
    protocol_match = re.match(r'^(?P<p>http|https|socks4|socks5)://', s, re.IGNORECASE)
    if protocol_match:
        protocol = protocol_match.group('p').lower()
        s = s[len(protocol_match.group('p'))+3:]

    def is_valid(ip, port):
        return port and port.isdigit()

    match = re.match(r'^([^:@]+):([^:@]+)@([^:@]+):(\d+)$', s)
    if match:
        user, password, ip, port = match.groups()
        if is_valid(ip, port): return build_dict(user, password, ip, port, protocol, proxy_input)

    match = re.match(r'^([^:@]+):([^:@]+)\s+([^:@]+):(\d+)$', s)
    if match:
        user, password, ip, port = match.groups()
        if is_valid(ip, port): return build_dict(user, password, ip, port, protocol, proxy_input)

    match = re.match(r'^([^:@]+):(\d+)\s+([^:@]+)\s+([^:@]+)$', s)
    if match:
        ip, port, user, password = match.groups()
        if is_valid(ip, port): return build_dict(user, password, ip, port, protocol, proxy_input)

    match = re.match(r'^([^:@]+)\s+([^:@]+)\s+([^:@]+):(\d+)$', s)
    if match:
        user, password, ip, port = match.groups()
        if is_valid(ip, port): return build_dict(user, password, ip, port, protocol, proxy_input)

    match = re.match(r'^([^:@]+)\s+([^:@]+)\s+([^:@]+)\s+(\d+)$', s)
    if match:
        user, password, ip, port = match.groups()
        if is_valid(ip, port): return build_dict(user, password, ip, port, protocol, proxy_input)

    match = re.match(r'^([^:@]+):([^:@]+):([^:@]+):(\d+)$', s)
    if match:
        user, password, ip, port = match.groups()
        if is_valid(ip, port): return build_dict(user, password, ip, port, protocol, proxy_input)

    match = re.match(r'^([^:@]+):(\d+):([^:@]+):([^:@]+)$', s)
    if match:
        ip, port, user, password = match.groups()
        if is_valid(ip, port): return build_dict(user, password, ip, port, protocol, proxy_input)

    return None

def build_dict(user, password, ip, port, protocol, original_input):
    encoded_user = quote(user, safe='')
    encoded_pass = quote(password, safe='')
    return {
        "user": user,
        "password": password,
        "ip": ip,
        "port": port,
        "original_format": original_input,
        "url_format": f"{protocol}://{encoded_user}:{encoded_pass}@{ip}:{port}",
        "db_format": f"{user} {password} {ip} {port}",
        "http_format": f"http://{user}:{password}@{ip}:{port}"
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MONGODB HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_db():
    client = MongoClient(MONGO_URI)
    return client["MASTER_DATABASE"], client

def _save_proxies(user_id, proxies):
    db, client = _get_db()
    proxies_col = db["proxies"]
    existing = set()
    for p in proxies_col.find({"user_id": user_id}, {"proxy": 1}):
        existing.add(p.get("proxy"))
    
    added = 0
    for p_str in proxies:
        if p_str not in existing:
            proxies_col.insert_one({"user_id": user_id, "proxy": p_str})
            existing.add(p_str)
            added += 1
    client.close()
    return added

def _get_user_proxies(user_id):
    db, client = _get_db()
    proxies_col = db["proxies"]
    rows = list(proxies_col.find({"user_id": user_id}))
    client.close()
    return rows

def _clear_proxies(user_id):
    db, client = _get_db()
    proxies_col = db["proxies"]
    result = proxies_col.delete_many({"user_id": user_id})
    client.close()
    return result.deleted_count

def _delete_proxies_by_ids(ids):
    db, client = _get_db()
    proxies_col = db["proxies"]
    result = proxies_col.delete_many({"_id": {"$in": ids}})
    client.close()
    return result.deleted_count

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROXY CHECKER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def check_proxy_live(proxy_url, session=None, timeout=PROXY_TIMEOUT):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    client_timeout = aiohttp.ClientTimeout(total=timeout, connect=timeout/2)
    
    close_session = False
    if session is None:
        session = aiohttp.ClientSession(timeout=client_timeout, headers=headers)
        close_session = True
    
    try:
        async with session.get(IPIFY_API_URL, proxy=proxy_url, ssl=False) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json()
                    ip = data.get('ip')
                    if ip:
                        return True, {"ip": ip}
                    return False, {"error": "No IP in response"}
                except Exception:
                    text_data = await resp.text()
                    if text_data.strip():
                        return True, {"ip": text_data.strip()}
                    return False, {"error": "Empty response"}
            else:
                return False, {"error": f"HTTP {resp.status}"}
    except asyncio.TimeoutError:
        return False, {"error": "Timeout"}
    except Exception as e:
        return False, {"error": str(e)[:80]}
    finally:
        if close_session:
            await session.close()

async def check_proxies_parallel(proxies_list, max_concurrent=MAX_CONCURRENT_CHECKS):
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []
    
    async def check_with_semaphore(proxy_data):
        async with semaphore:
            is_live, info = await check_proxy_live(proxy_data['url_format'])
            return (proxy_data, is_live, info)
    
    tasks = [check_with_semaphore(p) for p in proxies_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append((proxies_list[i], False, {"error": str(result)}))
        else:
            processed_results.append(result)
    
    return processed_results

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKGROUND TASKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def process_proxies_background(bot, message, valid_proxies):
    user_id = message.from_user.id
    total_count = len(valid_proxies)
    
    status_msg = await message.reply(
        f"⏳ <b>Processing...</b>\n\n<code>{total_count}</code> proxies to check",
        parse_mode="HTML"
    )
    
    results_list = await check_proxies_parallel(valid_proxies)
    
    live_count = sum(1 for _, is_live, _ in results_list if is_live)
    dead_count = total_count - live_count
    
    to_save = [proxy_data['db_format'] for proxy_data, is_live, _ in results_list if is_live]
    
    added_count = 0
    if to_save:
        try:
            added_count = await asyncio.to_thread(_save_proxies, user_id, to_save)
        except Exception as e:
            logging.error(f"DB Error: {e}")

    caption = (
        f"<b>✅ Complete!</b>\n\n"
        f"<b>Total ➛</b> <code>{total_count}</code>\n"
        f"<b>Live ➛</b> <b>{live_count}</b> ✅\n"
        f"<b>Added ➛</b> <b>{added_count}</b> 💾\n"
        f"<b>Dead ➛</b> <b>{dead_count}</b> ❌"
    )
    
    await bot.edit_message_text(caption, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="HTML")

async def check_db_proxies_background(bot, message):
    user_id = message.from_user.id
    
    rows = await asyncio.to_thread(_get_user_proxies, user_id)
    if not rows:
        await message.reply("<b>📭 No proxies saved.</b>", parse_mode="HTML")
        return

    total_count = len(rows)
    
    status_msg = await message.reply(
        f"⏳ <b>Checking...</b>\n\n<code>{total_count}</code> saved proxies",
        parse_mode="HTML"
    )
    
    proxies_to_check = []
    proxy_id_map = {}
    
    for doc in rows:
        proxy_str = doc.get("proxy")
        parsed = parse_proxy_input(proxy_str)
        if parsed:
            proxies_to_check.append(parsed)
            proxy_id_map[len(proxies_to_check)-1] = doc.get("_id")
    
    results_list = await check_proxies_parallel(proxies_to_check)
    
    dead_ids = []
    live_proxies = []
    
    for idx, (proxy_data, is_live, info) in enumerate(results_list):
        db_id = proxy_id_map.get(idx)
        if is_live:
            live_proxies.append(proxy_data['db_format'])
        else:
            if db_id:
                dead_ids.append(db_id)
    
    if dead_ids:
        await asyncio.to_thread(_delete_proxies_by_ids, dead_ids)

    caption = (
        f"<b>✅ Check Complete!</b>\n\n"
        f"<b>Total ➛</b> <code>{total_count}</code>\n"
        f"<b>Live ➛</b> <b>{len(live_proxies)}</b> ✅\n"
        f"<b>Removed ➛</b> <b>{len(dead_ids)}</b> 🗑️"
    )

    if not live_proxies:
        caption += "\n\n<b>⚠️ No live proxies remaining.</b>"
        await bot.edit_message_text(caption, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
        return

    file_content = "\n".join(live_proxies)
    txt_file = BufferedInputFile(file=file_content.encode('utf-8'), filename=f"live_proxies_{len(live_proxies)}.txt")
    
    try:
        await bot.delete_message(chat_id=status_msg.chat.id, message_id=status_msg.message_id)
    except:
        pass
    
    await message.reply_document(document=txt_file, caption=caption, parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.message(F.text.startswith("/proxy"))
async def proxy_command(message: types.Message):
    raw_text = ""
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        raw_text += parts[1].strip() + "\n"
    if message.reply_to_message and message.reply_to_message.text:
        raw_text += message.reply_to_message.text + "\n"
    if message.reply_to_message and message.reply_to_message.caption:
        raw_text += message.reply_to_message.caption + "\n"

    document = message.document
    if document:
        if document.file_size > 2 * 1024 * 1024:
            await message.reply("<b>❌ File too large.</b>", parse_mode="HTML")
            return
        try:
            file = await message.bot.get_file(document.file_id)
            byte_content = await file.download_as_bytearray()
            raw_text += byte_content.decode('utf-8', errors='ignore')
        except Exception as e:
            await message.reply(f"<b>❌ Error reading file: {e}</b>", parse_mode="HTML")
            return

    if not raw_text.strip():
        await message.reply("<b>⚠️ Invalid Usage!</b>\nUse: /proxy proxy:port or file", parse_mode="HTML")
        return

    lines = raw_text.strip().split('\n')
    valid_proxies = []
    for line in lines:
        proxy_data = parse_proxy_input(line)
        if proxy_data:
            valid_proxies.append(proxy_data)
            
    if not valid_proxies:
        await message.reply("<b>❌ No valid proxies found.</b>", parse_mode="HTML")
        return

    asyncio.create_task(process_proxies_background(message.bot, message, valid_proxies))

@router.message(F.text.startswith("/checkproxy"))
async def checkproxy_command(message: types.Message):
    asyncio.create_task(check_db_proxies_background(message.bot, message))

@router.message(F.text.startswith("/clearproxy"))
async def clearproxy_command(message: types.Message):
    user_id = message.from_user.id
    count = await asyncio.to_thread(_clear_proxies, user_id)
    if count > 0:
        await message.reply(f"<b>✅ Deleted {count} proxies.</b>", parse_mode="HTML")
    else:
        await message.reply("<b>📭 No proxies to delete.</b>", parse_mode="HTML")

@router.message(F.text.startswith("/myproxies"))
async def myproxies_command(message: types.Message):
    user_id = message.from_user.id
    rows = await asyncio.to_thread(_get_user_proxies, user_id)
    count = len(rows)
    if count > 0:
        await message.reply(
            f"<b>📊 Your Proxies</b>\n\n<b>Total Saved:</b> <b>{count}</b>\n\nUse /checkproxy to test them",
            parse_mode="HTML"
        )
    else:
        await message.reply("<b>📭 No proxies saved. Use /proxy to add.</b>", parse_mode="HTML")
