"""
Card Cleaning Utility - Shared across all mass gates
Handles dirty file formats, extracts valid cards
"""

import re

def clean_cards(raw_text):
    """
    Clean and extract valid cards from dirty text.
    Supports:
    - CC|MM|YY|CVV
    - CC|MM|YYYY|CVV
    - CC MM YY CVV (spaces)
    - CC/MM/YY/CVV
    - Cards separated by newlines, spaces, commas
    - Cards with extra text around them
    """
    cards = []
    
    # Normalize: replace common separators with |
    normalized = raw_text
    # Replace spaces, slashes, dashes, commas with pipe
    normalized = re.sub(r'[ ,/\-_\t]+', '|', normalized)
    
    # Find all card patterns (15-16 digits + 3-4 fields)
    # Pattern: 15-16 digits, then 3-4 groups of digits separated by |
    pattern = r'(\d{15,16})\|(\d{1,4})\|(\d{2,4})\|(\d{3,4})'
    matches = re.findall(pattern, normalized)
    
    for match in matches:
        cc, mm, yy, cvv = match
        
        # Clean each part
        cc = re.sub(r'\D', '', cc)  # Keep only digits
        mm = re.sub(r'\D', '', mm).zfill(2)
        
        # Handle year (4-digit or 2-digit)
        yy_clean = re.sub(r'\D', '', yy)
        if len(yy_clean) == 4:
            yy = yy_clean[2:]
        else:
            yy = yy_clean.zfill(2)
        
        cvv = re.sub(r'\D', '', cvv)[:4]
        
        # Validate
        if len(cc) >= 15 and len(mm) == 2 and len(yy) == 2 and len(cvv) >= 3:
            cards.append(f"{cc}|{mm}|{yy}|{cvv}")
    
    # Also try to find cards with different separators
    # Pattern: 15-16 digits, 2-4 digits, 2-4 digits, 3-4 digits
    alt_pattern = r'(\d{15,16})[|\s/:,.-]+(\d{1,4})[|\s/:,.-]+(\d{2,4})[|\s/:,.-]+(\d{3,4})'
    alt_matches = re.findall(alt_pattern, raw_text)
    
    for match in alt_matches:
        cc, mm, yy, cvv = match
        cc = re.sub(r'\D', '', cc)
        mm = re.sub(r'\D', '', mm).zfill(2)
        yy_clean = re.sub(r'\D', '', yy)
        yy = yy_clean[2:] if len(yy_clean) == 4 else yy_clean.zfill(2)
        cvv = re.sub(r'\D', '', cvv)[:4]
        
        if len(cc) >= 15 and len(mm) == 2 and len(yy) == 2 and len(cvv) >= 3:
            card = f"{cc}|{mm}|{yy}|{cvv}"
            if card not in cards:
                cards.append(card)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_cards = []
    for card in cards:
        if card not in seen:
            seen.add(card)
            unique_cards.append(card)
    
    return unique_cards

def mask_card(card):
    """Mask card for display: 4127......9457|12|2026|"""
    parts = card.split('|')
    if len(parts) >= 4:
        cc = parts[0]
        mm = parts[1]
        yy = parts[2]
        cvv = parts[3] if len(parts) > 3 else '***'
        return f"{cc[:4]}......{cc[-4:]}|{mm}|{yy}|{cvv[:3]}"
    return card[:20] + '...' if len(card) > 20 else card
