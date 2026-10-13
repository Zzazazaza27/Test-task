import pytest
from app.service import OrderSynchronizer

def test_deduplication_rules(tmp_path):
    db_file = str(tmp_path / "test.db")
    service = OrderSynchronizer(db_path=db_file)

    sample_orders = [
        # Group 1: Different amounts -> higher amount wins
        {"id": 1, "name": "User Low", "phone": "+7 999 000-00-01", "email": "low@test.com", "amount": 100, "created_at": "2026-10-01T10:00:00Z"},
        {"id": 2, "name": "User High", "phone": "8 (999) 000 00 01", "email": "high@test.com", "amount": 500, "created_at": "2026-10-01T09:00:00Z"},
        
        # Group 2: Equal amounts -> later created_at wins
        {"id": 3, "name": "User Early", "phone": "+7 999 000-00-02", "email": "early@test.com", "amount": 300, "created_at": "2026-10-01T10:00:00Z"},
        {"id": 4, "name": "User Late", "phone": "8-999-000-00-02", "email": "late@test.com", "amount": 300, "created_at": "2026-10-02T10:00:00Z"},
        
        # Group 3: Invalid phones
        {"id": 5, "name": "User Bad1", "phone": "123", "email": "bad1@test.com", "amount": 1000, "created_at": "2026-10-01T00:00:00Z"},
        {"id": 6, "name": "User Bad2", "phone": "", "email": "bad2@test.com", "amount": 1000, "created_at": "2026-10-01T00:00:00Z"},
    ]

    _, winners, stats = service.process_and_deduplicate(sample_orders)

    assert stats.received == 6
    assert stats.invalid_dropped == 2
    assert stats.unique == 2
    assert stats.duplicates_merged == 2

    winner_map = {w["phone"]: w for w in winners}
    
    # Check Group 1 winner
    assert winner_map["+79990000001"]["name"] == "User High"
    assert winner_map["+79990000001"]["amount"] == 500

    # Check Group 2 winner
    assert winner_map["+79990000002"]["name"] == "User Late"
    assert winner_map["+79990000002"]["amount"] == 300
