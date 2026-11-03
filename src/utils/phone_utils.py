from __future__ import annotations

import re


def normalize_phone_number(
    raw_phone: str,
    default_country_code: str = "595",
    validate: bool = True,
) -> str:
    """Cleans and normalizes phone strings into standard numeric E.164 digits without plus.

    Handles local zero-prefixed numbers (e.g. 0981... -> 595981...), international prefixes,
    dashes, spaces, parentheses, and WhatsApp JID suffixes (@s.whatsapp.net).

    Args:
        raw_phone: Raw input phone string or WhatsApp JID.
        default_country_code: Default ISO country calling code (default '595' for Paraguay).
        validate: If True, raises ValueError when the result fails E.164 length limits (7-15 digits).

    Returns:
        String containing only numeric digits compliant with E.164.

    Raises:
        ValueError: If input is empty, non-numeric, or fails length validation.
    """
    if not raw_phone or not isinstance(raw_phone, str):
        if validate:
            raise ValueError(f"Invalid phone number input: {raw_phone!r}")
        return ""

    text = raw_phone.strip()

    # If it is a WhatsApp JID, extract user portion
    if "@" in text:
        text = text.split("@")[0]

    # Remove all non-digit characters
    digits = re.sub(r"\D", "", text)

    if not digits:
        if validate:
            raise ValueError(f"No digits found in phone number input: {raw_phone!r}")
        return ""

    clean_country_code = re.sub(r"\D", "", default_country_code)

    # Specific normalization rules for default country code (Paraguay 595)
    if clean_country_code == "595":
        # e.g., 00595981... -> strip leading 00
        if digits.startswith("00595"):
            digits = digits[2:]
        # e.g., 0981... or 0971... -> strip 0 and prepend 595
        elif digits.startswith("0") and len(digits) >= 9:
            digits = "595" + digits[1:]
        # e.g., 981123456 (9 digits starting with 9) -> prepend 595
        elif len(digits) == 9 and digits.startswith("9"):
            digits = "595" + digits
    else:
        # Generic leading 00 international prefix
        if digits.startswith("00"):
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) >= 8:
            digits = clean_country_code + digits[1:]

    # ITU-T E.164 recommendation defines length between 7 and 15 digits
    if validate:
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError(
                f"Phone number '{digits}' (from '{raw_phone}') violates E.164 length (7-15 digits)"
            )

    return digits


def format_phone_e164(
    phone: str,
    with_plus: bool = True,
    default_country_code: str = "595",
) -> str:
    """Normalizes and formats a phone number as an E.164 string with optional '+' prefix."""
    digits = normalize_phone_number(
        phone, default_country_code=default_country_code, validate=True
    )
    return f"+{digits}" if with_plus else digits


def is_valid_phone_number(
    raw_phone: str,
    default_country_code: str = "595",
) -> bool:
    """Checks whether a phone number can be successfully normalized into a valid E.164 string."""
    try:
        normalize_phone_number(
            raw_phone, default_country_code=default_country_code, validate=True
        )
        return True
    except (ValueError, TypeError):
        return False


def to_whatsapp_jid(
    raw_phone: str,
    default_country_code: str = "595",
) -> str:
    """Normalizes phone number and returns the WhatsApp individual JID (e.g. '595981...@s.whatsapp.net')."""
    if "@g.us" in raw_phone:
        # Preserve group JIDs
        return raw_phone.strip()
    digits = normalize_phone_number(
        raw_phone, default_country_code=default_country_code, validate=True
    )
    return f"{digits}@s.whatsapp.net"
