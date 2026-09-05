import re

with open('msh.py', 'r') as f:
    content = f.read()

# Fix the API URL - add site parameter
content = re.sub(
    r'SH_API = "http://72\.61\.18\.119:7009/shopify\?cc={cc}"',
    'SH_API = "http://72.61.18.119:7009/shopify?cc={cc}&site={site}"',
    content
)

# Fix process_single_card to include site
# Replace the function with one that includes site
old_func = '''def process_single_card(card):
    try:
        resp = requests.get(SH_API.format(cc=card), timeout=90, verify=False)'''

new_func = '''def process_single_card(card, site=None):
    if site is None:
        site = "https://myfetaldoppler.com"
    try:
        resp = requests.get(SH_API.format(cc=card, site=site), timeout=90, verify=False)'''

content = content.replace(old_func, new_func)

# Also fix the call in the loop
content = re.sub(
    r'result = process_single_card\(card\)',
    'result = process_single_card(card, site="https://myfetaldoppler.com")',
    content
)

with open('msh.py', 'w') as f:
    f.write(content)

print("✅ msh.py fixed - site parameter added")
