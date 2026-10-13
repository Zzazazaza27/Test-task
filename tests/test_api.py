import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.service import OrderSynchronizer

client = TestClient(app)

SAMPLE_RAW_ORDERS = [
    {"id": 1, "name": "Иван Петров", "phone": "+7 999 123-45-67", "email": "ivan@example.com", "amount": 1000, "created_at": "2026-10-01T10:00:00Z"},
    {"id": 2, "name": "Иван П.", "phone": "8 (999) 123 45 67", "email": "", "amount": 5000, "created_at": "2026-10-02T11:00:00Z"},
    {"id": 14, "name": "Без телефона", "phone": "123", "email": "x1@example.com", "amount": 999, "created_at": "2026-10-01T00:00:00Z"},
]

@patch.object(OrderSynchronizer, "fetch_raw_orders", new_callable=AsyncMock)
def test_get_result_api(mock_fetch):
    mock_fetch.return_value = SAMPLE_RAW_ORDERS
    
    response = client.get("/result")
    assert response.status_code == 200
    data = response.json()
    
    assert "clients" in data
    assert "stats" in data
    assert data["stats"]["received"] == 3
    assert data["stats"]["unique"] == 1
    assert data["stats"]["duplicates_merged"] == 1
    assert data["stats"]["invalid_dropped"] == 1
    
    assert len(data["clients"]) == 1
    assert data["clients"][0]["phone"] == "+79991234567"
    assert data["clients"][0]["amount"] == 5000
    assert data["clients"][0]["name"] == "Иван П."

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
