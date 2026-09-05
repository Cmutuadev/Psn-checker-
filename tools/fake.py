"""
Fake Info Generator
Command: /fake
Usage: /fake [country_code/country_name]
Example: /fake us, /fake kenya, /fake et
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import random
import re
import asyncio
from datetime import datetime

# Try to import dependencies, fallback if not available
try:
    import httpx
except ImportError:
    httpx = None

try:
    import pycountry
except ImportError:
    pycountry = None

try:
    from faker import Faker
except ImportError:
    Faker = None

try:
    from countryinfo import CountryInfo
except ImportError:
    CountryInfo = None

router = Router()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COUNTRY DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOCALES = {
    'us': ('en_US', '🇺🇸'), 'ca': ('en_CA', '🇨🇦'), 'mx': ('es_MX', '🇲🇽'),
    'uk': ('en_GB', '🇬🇧'), 'gb': ('en_GB', '🇬🇧'), 'ie': ('en_IE', '🇮🇪'),
    'fr': ('fr_FR', '🇫🇷'), 'de': ('de_DE', '🇩🇪'), 'it': ('it_IT', '🇮🇹'),
    'es': ('es_ES', '🇪🇸'), 'pt': ('pt_PT', '🇵🇹'), 'nl': ('nl_NL', '🇳🇱'),
    'be': ('nl_BE', '🇧🇪'), 'ch': ('de_CH', '🇨🇭'), 'at': ('de_AT', '🇦🇹'),
    'se': ('sv_SE', '🇸🇪'), 'no': ('no_NO', '🇳🇴'), 'fi': ('fi_FI', '🇫🇮'),
    'dk': ('da_DK', '🇩🇰'), 'pl': ('pl_PL', '🇵🇱'), 'ru': ('ru_RU', '🇷🇺'),
    'ua': ('uk_UA', '🇺🇦'), 'gr': ('el_GR', '🇬🇷'), 'tr': ('tr_TR', '🇹🇷'),
    'cn': ('zh_CN', '🇨🇳'), 'jp': ('ja_JP', '🇯🇵'), 'kr': ('ko_KR', '🇰🇷'),
    'in': ('en_IN', '🇮🇳'), 'pk': ('ur_PK', '🇵🇰'), 'bd': ('bn_BD', '🇧🇩'),
    'sg': ('en_SG', '🇸🇬'), 'my': ('ms_MY', '🇲🇾'), 'id': ('id_ID', '🇮🇩'),
    'th': ('th_TH', '🇹🇭'), 'vn': ('vi_VN', '🇻🇳'), 'ph': ('en_PH', '🇵🇭'),
    'au': ('en_AU', '🇦🇺'), 'nz': ('en_NZ', '🇳🇿'), 'za': ('en_ZA', '🇿🇦'),
    'ng': ('en_NG', '🇳🇬'), 'gh': ('en_GH', '🇬🇭'), 'ke': ('en_US', '🇰🇪'),
    'tz': ('en_US', '🇹🇿'), 'ug': ('en_US', '🇺🇬'), 'et': ('en_US', '🇪🇹'),
    'eg': ('ar_EG', '🇪🇬'), 'ma': ('ar_MA', '🇲🇦'), 'dz': ('ar_DZ', '🇩🇿'),
    'sa': ('ar_SA', '🇸🇦'), 'ae': ('ar_AE', '🇦🇪'), 'il': ('he_IL', '🇮🇱'),
    'br': ('pt_BR', '🇧🇷'), 'ar': ('es_AR', '🇦🇷'), 'cl': ('es_CL', '🇨🇱'),
    'co': ('es_CO', '🇨🇴'), 'pe': ('es_PE', '🇵🇪'), 've': ('es_VE', '🇻🇪'),
}

# Country name to code mapping
COUNTRY_NAME_TO_CODE = {}
if pycountry:
    for country in pycountry.countries:
        code = country.alpha_2.lower()
        if code in LOCALES:
            COUNTRY_NAME_TO_CODE[country.name.lower()] = code
            if hasattr(country, 'common_name'):
                COUNTRY_NAME_TO_CODE[country.common_name.lower()] = code

# Manual mappings
COMMON_VARIATIONS = {
    'usa': 'us', 'america': 'us', 'united states': 'us',
    'britain': 'gb', 'england': 'gb', 'uk': 'gb',
    'russia': 'ru', 'china': 'cn', 'japan': 'jp', 'korea': 'kr',
    'india': 'in', 'pakistan': 'pk', 'bangladesh': 'bd',
    'brazil': 'br', 'argentina': 'ar', 'chile': 'cl',
    'australia': 'au', 'new zealand': 'nz', 'south africa': 'za',
    'kenya': 'ke', 'tanzania': 'tz', 'uganda': 'ug',
    'ethiopia': 'et', 'nigeria': 'ng', 'ghana': 'gh',
    'egypt': 'eg', 'morocco': 'ma', 'algeria': 'dz',
    'saudi arabia': 'sa', 'uae': 'ae', 'israel': 'il',
    'france': 'fr', 'germany': 'de', 'italy': 'it',
    'spain': 'es', 'portugal': 'pt', 'netherlands': 'nl',
}
COUNTRY_NAME_TO_CODE.update(COMMON_VARIATIONS)

def get_country_code(query: str) -> str:
    query = query.lower().strip()
    if query in LOCALES:
        return query
    if query in COUNTRY_NAME_TO_CODE:
        return COUNTRY_NAME_TO_CODE[query]
    # Try partial match
    for name, code in COUNTRY_NAME_TO_CODE.items():
        if query in name or name in query:
            return code
    return 'us'  # Default

def generate_phone(country_code: str) -> str:
    """Generate realistic phone number for country."""
    patterns = {
        'us': lambda: f"+1 {random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
        'uk': lambda: f"+44 {random.randint(7000,7999)} {random.randint(100000,999999)}",
        'de': lambda: f"+49 {random.randint(150,179)} {random.randint(1000000,9999999)}",
        'fr': lambda: f"+33 {random.randint(600,799)} {random.randint(100000,999999)}",
        'it': lambda: f"+39 {random.randint(300,399)} {random.randint(1000000,9999999)}",
        'es': lambda: f"+34 {random.randint(600,699)} {random.randint(100000,999999)}",
        'ru': lambda: f"+7 {random.randint(900,999)} {random.randint(1000000,9999999)}",
        'in': lambda: f"+91 {random.randint(70000,99999)} {random.randint(10000,99999)}",
        'cn': lambda: f"+86 {random.randint(130,199)} {random.randint(10000000,99999999)}",
        'jp': lambda: f"+81 {random.randint(70,90)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
        'br': lambda: f"+55 {random.randint(11,99)} {random.randint(90000,99999)}-{random.randint(1000,9999)}",
        'au': lambda: f"+61 {random.randint(400,499)} {random.randint(100000,999999)}",
        'za': lambda: f"+27 {random.randint(60,89)} {random.randint(1000000,9999999)}",
        'ke': lambda: f"+254 {random.randint(700,799)} {random.randint(100000,999999)}",
        'ng': lambda: f"+234 {random.randint(800,899)} {random.randint(1000000,9999999)}",
        'eg': lambda: f"+20 {random.randint(100,199)} {random.randint(1000000,9999999)}",
        'ma': lambda: f"+212 {random.randint(600,699)} {random.randint(100000,999999)}",
        'sa': lambda: f"+966 {random.randint(50,59)} {random.randint(1000000,9999999)}",
        'ae': lambda: f"+971 {random.randint(50,59)} {random.randint(1000000,9999999)}",
        'tr': lambda: f"+90 {random.randint(500,599)} {random.randint(1000000,9999999)}",
        'ph': lambda: f"+63 {random.randint(900,999)} {random.randint(1000000,9999999)}",
        'vn': lambda: f"+84 {random.randint(90,99)} {random.randint(10000000,99999999)}",
        'th': lambda: f"+66 {random.randint(60,69)} {random.randint(1000000,9999999)}",
    }
    pattern = patterns.get(country_code, patterns.get('us'))
    return pattern()

def generate_email(first_name: str, last_name: str, country_code: str) -> str:
    """Generate realistic email."""
    domains = {
        'us': ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com'],
        'uk': ['gmail.com', 'yahoo.co.uk', 'hotmail.co.uk', 'outlook.com'],
        'de': ['gmail.com', 'yahoo.de', 'web.de', 'gmx.de'],
        'fr': ['gmail.com', 'yahoo.fr', 'orange.fr', 'outlook.com'],
        'in': ['gmail.com', 'yahoo.in', 'rediffmail.com', 'outlook.com'],
        'ke': ['gmail.com', 'yahoo.com', 'outlook.com', 'safaricom.co.ke'],
        'ng': ['gmail.com', 'yahoo.com', 'outlook.com', 'nigeria-mail.com'],
        'za': ['gmail.com', 'yahoo.com', 'outlook.com', 'webmail.co.za'],
        'ae': ['gmail.com', 'yahoo.com', 'hotmail.com', 'emirates.net.ae'],
        'sa': ['gmail.com', 'yahoo.com', 'hotmail.com', 'yahoo.com.sa'],
        'tr': ['gmail.com', 'yahoo.com', 'mynet.com', 'outlook.com'],
        'ru': ['gmail.com', 'yandex.ru', 'mail.ru', 'outlook.com'],
        'cn': ['gmail.com', '163.com', 'qq.com', '126.com'],
        'jp': ['gmail.com', 'yahoo.co.jp', 'outlook.jp', 'icloud.com'],
        'br': ['gmail.com', 'yahoo.com.br', 'outlook.com', 'uol.com.br'],
        'au': ['gmail.com', 'yahoo.com.au', 'outlook.com', 'bigpond.com'],
    }
    domain_list = domains.get(country_code, ['gmail.com', 'yahoo.com', 'outlook.com'])
    
    f = first_name.lower().replace(' ', '').replace('-', '')
    l = last_name.lower().replace(' ', '').replace('-', '')
    
    patterns = [
        f"{f}{random.randint(1,99)}",
        f"{f}.{l}",
        f"{f}_{l}",
        f"{f[0]}{l}",
        f"{f}{l[0]}",
        f"{l}.{f}",
        f"{l}{f[0]}",
        f"{f}",
    ]
    username = random.choice(patterns)
    return f"{username}@{random.choice(domain_list)}"

def generate_address(country_code: str) -> dict:
    """Generate realistic address for country."""
    streets = {
        'us': ['Main St', 'Park Ave', 'Oak Dr', 'Maple Rd', 'Washington Blvd', 'Cedar Ln'],
        'uk': ['High Street', 'Church Road', 'Station Road', 'Victoria Road', 'Green Lane'],
        'de': ['Hauptstraße', 'Kirchstraße', 'Schulstraße', 'Bahnhofstraße', 'Goethestraße'],
        'fr': ['Rue de la Paix', 'Avenue des Champs', 'Rue du Faubourg', 'Boulevard Saint-Germain'],
        'ke': ['Moi Avenue', 'Kenyatta Avenue', 'Ngong Road', 'Langata Road', 'Thika Road'],
        'ng': ['Lekki Road', 'Ikeja Road', 'Victoria Island', 'Ajah Road', 'Murtala Muhammed Way'],
        'za': ['Main Road', 'Park Street', 'Church Road', 'River Lane', 'Mountain Drive'],
        'et': ['Bole Road', 'Kazanchis', 'Piassa', 'Arat Kilo', 'Mexico Road', 'Gerji Road'],
    }
    
    cities = {
        'us': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia'],
        'uk': ['London', 'Manchester', 'Birmingham', 'Glasgow', 'Liverpool', 'Edinburgh'],
        'de': ['Berlin', 'Munich', 'Hamburg', 'Cologne', 'Frankfurt', 'Stuttgart'],
        'fr': ['Paris', 'Marseille', 'Lyon', 'Toulouse', 'Nice', 'Nantes'],
        'ke': ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika'],
        'ng': ['Lagos', 'Kano', 'Ibadan', 'Abuja', 'Port Harcourt', 'Benin City'],
        'za': ['Cape Town', 'Johannesburg', 'Durban', 'Pretoria', 'Port Elizabeth'],
        'et': ['Addis Ababa', 'Dire Dawa', 'Mekele', 'Gondar', 'Adama', 'Hawassa'],
    }
    
    states = {
        'us': ['CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI'],
        'uk': ['England', 'Scotland', 'Wales', 'Northern Ireland'],
        'de': ['Bavaria', 'Berlin', 'Hamburg', 'Hesse', 'North Rhine-Westphalia'],
        'fr': ['Île-de-France', 'Provence-Alpes-Côte d\'Azur', 'Auvergne-Rhône-Alpes'],
        'ke': ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Kiambu', 'Uasin Gishu'],
        'ng': ['Lagos', 'Kano', 'Oyo', 'Rivers', 'Abuja', 'Kaduna'],
        'za': ['Gauteng', 'Western Cape', 'KwaZulu-Natal', 'Eastern Cape'],
        'et': ['Addis Ababa', 'Oromia', 'Amhara', 'Tigray', 'Sidama', 'Somali'],
    }
    
    street_list = streets.get(country_code, streets['us'])
    city_list = cities.get(country_code, cities['us'])
    state_list = states.get(country_code, states['us'])
    
    return {
        'street': f"{random.randint(1, 9999)} {random.choice(street_list)}",
        'city': random.choice(city_list),
        'state': random.choice(state_list),
        'postal_code': str(random.randint(10000, 99999)),
        'country_code': country_code
    }

def generate_african_name(gender: str, country_code: str) -> tuple:
    """Generate culturally appropriate African names."""
    # East African names
    east_african_male = ["Kamau", "Njoroge", "Mwangi", "Ochieng", "Otieno", "Odhiambo", 
                        "Baraka", "Emmanuel", "Moses", "Samuel", "David", "John"]
    east_african_female = ["Wanjiku", "Nyambura", "Wangari", "Njeri", "Achieng", "Atieno",
                          "Grace", "Faith", "Mary", "Sarah", "Naomi", "Ruth"]
    
    # West African names
    west_african_male = ["Adebayo", "Oluwaseun", "Chukwudi", "Emeka", "Kofi", "Kwame",
                        "Mohammed", "Ibrahim", "Musa", "Ali", "Hassan", "Amadou"]
    west_african_female = ["Abimbola", "Adenike", "Chioma", "Ngozi", "Ama", "Akua",
                          "Fatima", "Aisha", "Amina", "Zainab", "Khadija", "Maryam"]
    
    # North African names
    north_african_male = ["Mohammed", "Ahmed", "Youssef", "Mehdi", "Hamza", "Omar",
                         "Khalid", "Samir", "Jamal", "Karim", "Tarik", "Bilal"]
    north_african_female = ["Fatima", "Aisha", "Amina", "Leila", "Nadia", "Samira",
                           "Karima", "Layla", "Khadija", "Malika", "Naima", "Zahra"]
    
    # Southern African names
    southern_african_male = ["Sipho", "Thabo", "Themba", "Mandla", "Nkosi", "Bongani",
                            "Tafadzwa", "Tatenda", "Tendai", "Tanaka", "Tinashe", "Chipo"]
    southern_african_female = ["Thandi", "Nomvula", "Zanele", "Ntombi", "Siphokazi", "Nobuhle",
                              "Chiedza", "Nyasha", "Ruvarashe", "Rutendo", "Shamiso", "Tariro"]
    
    # Map country to region
    region = 'east'
    if country_code in ['ng', 'gh', 'sn', 'ci', 'ml', 'bf', 'bj', 'gm']:
        region = 'west'
    elif country_code in ['eg', 'ma', 'dz', 'tn', 'ly', 'sd']:
        region = 'north'
    elif country_code in ['za', 'zw', 'zm', 'na', 'bw', 'mz', 'ao']:
        region = 'south'
    elif country_code in ['et']:
        # Ethiopia specific - use Ethiopian names
        ethiopian_male = ["Abebe", "Bekele", "Demeke", "Getachew", "Haile", "Tadesse",
                         "Tesfaye", "Girma", "Melaku", "Yohannes", "Daniel", "Solomon"]
        ethiopian_female = ["Abeba", "Bethlehem", "Desta", "Genet", "Hiwot", "Meron",
                           "Rahel", "Seble", "Tigist", "Eden", "Selam", "Sara"]
        if gender.lower().startswith('m'):
            return random.choice(ethiopian_male), random.choice(['Abebe', 'Bekele', 'Demeke'])
        else:
            return random.choice(ethiopian_female), random.choice(['Abeba', 'Desta', 'Genet'])
    
    if region == 'east':
        if gender.lower().startswith('m'):
            return random.choice(east_african_male), random.choice(['Kipchoge', 'Kimutai', 'Korir'])
        else:
            return random.choice(east_african_female), random.choice(['Wambui', 'Njeri', 'Wangari'])
    elif region == 'west':
        if gender.lower().startswith('m'):
            return random.choice(west_african_male), random.choice(['Adeyemi', 'Okafor', 'Okonkwo'])
        else:
            return random.choice(west_african_female), random.choice(['Mensah', 'Owusu', 'Osei'])
    elif region == 'south':
        if gender.lower().startswith('m'):
            return random.choice(southern_african_male), random.choice(['Nkosi', 'Dlamini', 'Mkhize'])
        else:
            return random.choice(southern_african_female), random.choice(['Zuma', 'Mahlangu', 'Mokoena'])
    else:
        if gender.lower().startswith('m'):
            return random.choice(north_african_male), random.choice(['El Fassi', 'Bennani', 'Alaoui'])
        else:
            return random.choice(north_african_female), random.choice(['El Fassi', 'Bennani', 'Alaoui'])

@router.message(Command("fake"))
async def fake_command(message: types.Message):
    args = message.text.split()[1:]
    country_query = " ".join(args) if args else "us"
    
    # Get country code
    country_code = get_country_code(country_query)
    
    # Get locale and flag
    locale, flag = LOCALES.get(country_code, ('en_US', '🇺🇸'))
    
    # Create Faker instance
    try:
        if Faker:
            fake = Faker(locale)
        else:
            fake = None
    except Exception:
        fake = None
    
    # Generate gender
    gender = random.choice(['Male', 'Female'])
    
    # Generate name
    if country_code in ['ke', 'tz', 'ug', 'et', 'ng', 'gh', 'za', 'eg', 'ma', 'dz']:
        first_name, last_name = generate_african_name(gender, country_code)
        full_name = f"{first_name} {last_name}"
    else:
        if fake:
            first_name = fake.first_name()
            last_name = fake.last_name()
            full_name = f"{first_name} {last_name}"
        else:
            common_first = ["James", "John", "Robert", "Michael", "William", "Mary", "Patricia", "Linda"]
            common_last = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis"]
            first_name = random.choice(common_first)
            last_name = random.choice(common_last)
            full_name = f"{first_name} {last_name}"
    
    # Generate age
    age = random.randint(18, 70)
    birth_year = datetime.now().year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    birthdate = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
    
    # Generate address
    address = generate_address(country_code)
    
    # Generate phone
    phone = generate_phone(country_code)
    
    # Generate email
    email = generate_email(first_name, last_name, country_code)
    
    # Get country name
    if pycountry:
        country_obj = pycountry.countries.get(alpha_2=country_code.upper())
        country_name = country_obj.name if country_obj else country_code.upper()
    else:
        country_name = country_code.upper()
    
    # Build response
    response = (
        f"🌍 <b>𝗙𝗮𝗸𝗲 𝗜𝗻𝗳𝗼 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {flag} {country_name}\n"
        f"<b>𝗙𝘂𝗹𝗹 𝗡𝗮𝗺𝗲:</b> <code>{full_name}</code>\n"
        f"<b>𝗚𝗲𝗻𝗱𝗲𝗿:</b> {gender}\n"
        f"<b>𝗔𝗴𝗲:</b> {age} years\n"
        f"<b>𝗕𝗶𝗿𝘁𝗵𝗱𝗮𝘆:</b> {birthdate}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>𝗦𝘁𝗿𝗲𝗲𝘁:</b> <code>{address['street']}</code>\n"
        f"<b>𝗖𝗶𝘁𝘆:</b> <code>{address['city']}</code>\n"
        f"<b>𝗦𝘁𝗮𝘁𝗲/𝗣𝗿𝗼𝘃𝗶𝗻𝗰𝗲:</b> <code>{address['state']}</code>\n"
        f"<b>𝗣𝗼𝘀𝘁𝗮𝗹 𝗖𝗼𝗱𝗲:</b> <code>{address['postal_code']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>𝗣𝗵𝗼𝗻𝗲:</b> <code>{phone}</code>\n"
        f"<b>𝗘𝗺𝗮𝗶𝗹:</b> <code>{email}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>𝗗𝗲𝘃:</b> @npnbit4"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 𝗕𝗨𝗬 𝗡𝗢𝗪", url="https://t.me/npnbit4")]
    ])
    
    await message.reply(response, parse_mode="HTML", reply_markup=kb)

# Also handle .fake
@router.message(F.text.startswith(".fake"))
async def dot_fake_command(message: types.Message):
    # Extract args from the dot command
    args = message.text[5:].strip().split()
    # Reconstruct the message as if it was /fake
    new_text = "/fake " + " ".join(args) if args else "/fake"
    # Simulate the command
    fake_cmd = Command("fake")
    # We'll just call the handler directly
    await fake_command(message)
