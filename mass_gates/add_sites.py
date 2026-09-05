import re

with open('msh.py', 'r') as f:
    content = f.read()

# Check if random is imported
if 'import random' not in content:
    content = content.replace('import random', 'import random', 1)
    # If random not found, add it after other imports
    if 'import random' not in content:
        content = content.replace('import os', 'import os\nimport random')

# Add load_sites function after imports
load_sites_func = '''
def load_sites():
    sites = []
    try:
        if os.path.exists("sites.txt"):
            with open("sites.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if not line.startswith("http"):
                            line = "https://" + line
                        sites.append(line)
    except Exception as e:
        logging.error(f"Error loading sites: {e}")
    if not sites:
        sites = ["https://myfetaldoppler.com"]
    return sites
'''

# Insert load_sites before process_single_card
content = content.replace('def process_single_card(card, site=None):', load_sites_func + '\ndef process_single_card(card):')

# Update the function to use load_sites
old_func = '''def process_single_card(card):
    sites = load_sites()
    site = random.choice(sites) if sites else "https://myfetaldoppler.com"
    try:
        resp = requests.get(SH_API.format(cc=card, site=site), timeout=90, verify=False)'''

# Check if already updated
if 'sites = load_sites()' not in content:
    content = content.replace(
        'def process_single_card(card):',
        'def process_single_card(card):\n    sites = load_sites()\n    site = random.choice(sites) if sites else "https://myfetaldoppler.com"\n    try:\n        resp = requests.get(SH_API.format(cc=card, site=site), timeout=90, verify=False)'
    )

# Also fix the call in the loop
content = re.sub(
    r'result = process_single_card\(card, site="https://myfetaldoppler.com"\)',
    'result = process_single_card(card)',
    content
)

with open('msh.py', 'w') as f:
    f.write(content)

print("✅ msh.py updated to use sites.txt")
