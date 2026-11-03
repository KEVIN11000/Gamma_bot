import pytest
from utils.phone_utils import (
    format_phone_e164,
    is_valid_phone_number,
    normalize_phone_number,
    to_whatsapp_jid,
)


def test_normalize_local_paraguay_with_leading_zero():
    """Verifies that local zero-prefixed numbers are normalized to 595 country code."""
    assert normalize_phone_number("0981 123 456") == "595981123456"
    assert normalize_phone_number("0971-654-321") == "595971654321"
    assert normalize_phone_number("(0985) 999 888") == "595985999888"
    assert normalize_phone_number("021 444 555") == "59521444555"


def test_normalize_paraguay_international_prefixes():
    """Verifies numbers with +595 or 00595 are cleaned properly."""
    assert normalize_phone_number("+595 981 123 456") == "595981123456"
    assert normalize_phone_number("00595 981 123 456") == "595981123456"
    assert normalize_phone_number("595981123456") == "595981123456"


def test_normalize_paraguay_nine_digits():
    """Verifies 9-digit numbers starting with 9 have 595 prepended."""
    assert normalize_phone_number("981123456") == "595981123456"
    assert normalize_phone_number("971-999-888") == "595971999888"


def test_normalize_foreign_numbers():
    """Verifies that international numbers outside Paraguay are preserved accurately."""
    # Argentina
    assert normalize_phone_number("+54 9 11 1234-5678") == "5491112345678"
    # USA
    assert normalize_phone_number("+1 (415) 555-2671") == "14155552671"
    # Brazil
    assert normalize_phone_number("+55 11 98765-4321") == "5511987654321"


def test_normalize_whatsapp_jid():
    """Verifies that @s.whatsapp.net suffix is parsed and stripped."""
    assert normalize_phone_number("595981123456@s.whatsapp.net") == "595981123456"
    assert normalize_phone_number("0981123456@s.whatsapp.net") == "595981123456"


def test_format_phone_e164():
    """Verifies format_phone_e164 with and without plus sign."""
    assert format_phone_e164("0981 123 456", with_plus=True) == "+595981123456"
    assert format_phone_e164("0981 123 456", with_plus=False) == "595981123456"


def test_to_whatsapp_jid():
    """Verifies to_whatsapp_jid generation for direct chats and preservation of groups."""
    assert to_whatsapp_jid("0981 123 456") == "595981123456@s.whatsapp.net"
    assert to_whatsapp_jid("+54 9 11 1234 5678") == "5491112345678@s.whatsapp.net"

    # Group JID should be preserved
    group_jid = "120363041234567890@g.us"
    assert to_whatsapp_jid(group_jid) == group_jid


def test_is_valid_phone_number():
    """Verifies is_valid_phone_number boolean checks."""
    assert is_valid_phone_number("0981 123 456") is True
    assert is_valid_phone_number("+595981123456") is True
    assert is_valid_phone_number("+14155552671") is True

    # Invalid cases
    assert is_valid_phone_number("abc") is False
    assert is_valid_phone_number("") is False
    assert is_valid_phone_number("12345") is False  # too short
    assert is_valid_phone_number("12345678901234567") is False  # > 15 digits
    assert is_valid_phone_number(None) is False  # type: ignore[arg-type]


def test_invalid_phone_raises_value_error():
    """Verifies that invalid numbers raise ValueError when validate=True."""
    with pytest.raises(ValueError, match="Invalid phone number input"):
        normalize_phone_number("")

    with pytest.raises(ValueError, match="No digits found"):
        normalize_phone_number("invalid-phone-without-digits")

    with pytest.raises(ValueError, match="violates E.164 length"):
        normalize_phone_number("12345")  # < 7 digits

    with pytest.raises(ValueError, match="violates E.164 length"):
        normalize_phone_number("12345678901234567")  # > 15 digits
