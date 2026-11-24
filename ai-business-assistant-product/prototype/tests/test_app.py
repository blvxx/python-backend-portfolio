from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

def payload(question="Покажи неоплаченные счета", tenant="demo-alpha"):
    return {"question": question, "tenant_id": tenant}

def test_unpaid_invoices_returns_tenant_scoped_evidence():
    response = client.post("/v1/assistant/query", json=payload(), headers={"X-Demo-Tenant": "demo-alpha"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "unpaid_invoices"
    assert body["status"] == "answered"
    assert body["read_only"] is True
    assert body["evidence"][0]["record_ids"] == ["INV-A-1001", "INV-A-1002"]
    assert "INV-B-2001" not in str(body)

def test_missing_trusted_tenant_context_is_denied():
    response = client.post("/v1/assistant/query", json=payload())
    assert response.status_code == 403

def test_mismatched_tenant_is_denied():
    response = client.post("/v1/assistant/query", json=payload(), headers={"X-Demo-Tenant": "demo-beta"})
    assert response.status_code == 403

def test_paid_revenue_keeps_currencies_separate():
    response = client.post("/v1/assistant/query", json=payload("Покажи выручку"), headers={"X-Demo-Tenant": "demo-alpha"})
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "EUR 800.00" in answer
    assert "RUB 91000.00" in answer

def test_write_request_is_refused():
    response = client.post("/v1/assistant/query", json=payload("Отметь счёт оплаченным"), headers={"X-Demo-Tenant": "demo-alpha"})
    assert response.status_code == 200
    assert response.json()["status"] == "unsupported"
    assert response.json()["read_only"] is True

def test_unknown_intent_returns_safe_fallback():
    response = client.post("/v1/assistant/query", json=payload("Какая погода?"), headers={"X-Demo-Tenant": "demo-alpha"})
    assert response.status_code == 200
    assert response.json()["intent"] == "unknown"
