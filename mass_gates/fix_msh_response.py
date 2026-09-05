import re

with open('msh.py', 'r') as f:
    content = f.read()

# Fix the response parsing
old = '''        if resp.status_code == 200:
            data = resp.json()
            raw_message = data.get('message', 'Unknown')
            if data.get('approved', False) or is_approved_response(raw_message):
                return {"status": "APPROVED", "response": raw_message}
            else:
                return {"status": "DECLINED", "response": raw_message}'''

new = '''        if resp.status_code == 200:
            data = resp.json()
            raw_message = data.get('Response', data.get('message', 'Unknown'))
            status_field = data.get('Status', False)
            # If Status is True and Response is not CARD_DECLINED, it's approved
            if status_field and raw_message != "CARD_DECLINED":
                return {"status": "APPROVED", "response": raw_message}
            else:
                return {"status": "DECLINED", "response": raw_message}'''

content = content.replace(old, new)

with open('msh.py', 'w') as f:
    f.write(content)

print("✅ msh.py response parsing fixed")
