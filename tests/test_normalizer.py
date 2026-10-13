import pytest
from app.normalizer import normalize_phone

def test_normalize_valid_russian_formats():
    assert normalize_phone("+7 999 123-45-67") == "+79991234567"
    assert normalize_phone("8 (999) 123 45 67") == "+79991234567"
    assert normalize_phone("79991234567") == "+79991234567"
    assert normalize_phone("8-916-000-00-01") == "+79160000001"
    assert normalize_phone("+7 (916) 000 00 01") == "+79160000001"
    assert normalize_phone("8 903 111 22 33") == "+79031112233"
    assert normalize_phone("+79219998877") == "+79219998877"

def test_normalize_10_digits():
    assert normalize_phone("9005551212") == "+79005551212"
    assert normalize_phone("(900) 555-12-12") == "+79005551212"

def test_normalize_invalid_dropped():
    assert normalize_phone("123") is None
    assert normalize_phone("") is None
    assert normalize_phone(None) is None
    assert normalize_phone("не указан") is None
    assert normalize_phone("+7 999") is None
    assert normalize_phone("12345678901234") is None
    assert normalize_phone("abcdefghijk") is None
