import re
from typing import Optional

def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalizes raw phone number string to '+7XXXXXXXXXX' format.
    
    Rules:
    - Strips all non-digit characters.
    - 11 digits starting with '7' or '8' -> '+7' + last 10 digits.
    - 10 digits -> '+7' + 10 digits.
    - All other cases cannot be reduced to 11 Russian digits and return None (invalid).
    """
    if not phone or not isinstance(phone, str):
        return None
    
    digits = re.sub(r"\D", "", phone)
    
    if len(digits) == 11 and (digits.startswith("7") or digits.startswith("8")):
        return f"+7{digits[1:]}"
    elif len(digits) == 10:
        return f"+7{digits}"
    
    return None
