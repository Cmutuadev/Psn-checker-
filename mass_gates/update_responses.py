import re

for file in ['msh.py', '../gates/sh.py']:
    try:
        with open(file, 'r') as f:
            content = f.read()
        
        # Update DECLINED_RESPONSES
        new_declined = '''DECLINED_RESPONSES = [
    "CARD_DECLINED", "DECLINED", "DO_NOT_HONOR", "INVALID_CARD",
    "EXPIRED_CARD", "INCORRECT_NUMBER", "PICKUP_CARD", "LOST_OR_STOLEN",
    "PROCESSING_ERROR", "GENERIC_ERROR", "SYSTEM_ERROR"
]'''
        
        content = re.sub(r'DECLINED_RESPONSES = \[.*?\]', new_declined, content, flags=re.DOTALL)
        
        # Update get_response_status to check PROCESSING_ERROR
        if 'if "PROCESSING_ERROR" in response_text:' not in content:
            content = content.replace(
                'if "CARD_DECLINED" in response_text:',
                'if "PROCESSING_ERROR" in response_text:\n        return "DECLINED"\n    if "CARD_DECLINED" in response_text:'
            )
        
        with open(file, 'w') as f:
            f.write(content)
        print(f"✅ Updated {file}")
    except Exception as e:
        print(f"❌ Error updating {file}: {e}")
