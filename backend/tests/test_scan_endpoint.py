"""End-to-end scan endpoint tests."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_scan_legitimate_url(client):
    r = client.post("/api/v1/scan/url", json={"url": "https://www.google.com/"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in {"safe", "caution", "danger"}
    assert 0 <= body["risk_score"] <= 100
    assert isinstance(body["signals"], list)


def test_scan_typosquat_high_risk(client):
    r = client.post("/api/v1/scan/url", json={"url": "https://paypa1.com/login"})
    assert r.status_code == 200
    body = r.json()
    assert body["risk_score"] > 30


def test_merchant_endpoint_reserved(client):
    r = client.post(
        "/api/v1/merchant/scan",
        json={"url": "https://example.com/", "has_checkout_form": True},
    )
    assert r.status_code == 501
