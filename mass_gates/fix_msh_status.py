import re

with open('msh.py', 'r') as f:
    content = f.read()

# Fix process_single_card - check Response BEFORE Status
new_process = '''def process_single_card(card):
    sites = load_sites()
    site = random.choice(sites) if sites else "https://myfetaldoppler.com"
    try:
        resp = requests.get(SH_API.format(cc=card, site=site), timeout=30, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            raw_message = data.get('Response', data.get('message', 'Unknown'))
            status_field = data.get('Status', False)
            gateway = data.get('Gateway', 'Shopify')
            price = data.get('Price', '0.00')
            
            detected_status = get_response_status(raw_message)
            
            # CHECK RESPONSE FIRST - if it's CARD_DECLINED, it's DECLINED
            if detected_status == "DECLINED":
                return {"status": "DECLINED", "response": f"{raw_message} | {gateway}"}
            
            # THEN check if Status is True
            if status_field:
                return {"status": "APPROVED", "response": f"{raw_message} | {gateway} | ${price}"}
            
            # Then check approved
            if detected_status == "APPROVED":
                return {"status": "APPROVED", "response": f"{raw_message} | {gateway} | ${price}"}
            elif "site not supported" in raw_message.lower():
                remove_dead_site(site)
                return {"status": "ERROR", "response": "Site removed"}
            else:
                return {"status": "DECLINED", "response": f"{raw_message} | {gateway}"}
        else:
            remove_dead_site(site)
            return {"status": "ERROR", "response": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "ERROR", "response": str(e)[:80]}'''

# Find and replace the function
pattern = r'def process_single_card\(card\).*?(?=\n@router|\ndef |\Z)'
content = re.sub(pattern, new_process, content, flags=re.DOTALL)

with open('msh.py', 'w') as f:
    f.write(content)

print("✅ Fixed: Response checked before Status")
