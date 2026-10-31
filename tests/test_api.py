from fastapi.testclient import TestClient

from app.main import app
from app.schemas import InvoiceData, ResumeData


def test_health(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "provider": "ollama", "model": "test-model"}


def test_successful_resume_extraction(monkeypatch):
    expected = ResumeData(name="Jane Doe", email="jane@example.com", skills=["Python"])
    monkeypatch.setattr("app.main.extract_resume", lambda _: expected)
    response = TestClient(app).post("/extract/resume", json={"text": "Jane Doe, jane@example.com, Python"})
    assert response.status_code == 200
    assert response.json()["name"] == "Jane Doe"
    assert response.json()["skills"] == ["Python"]


def test_successful_invoice_extraction(monkeypatch):
    expected = InvoiceData(invoice_number="INV-1", total_amount=1200.5)
    monkeypatch.setattr("app.main.extract_invoice", lambda _: expected)
    response = TestClient(app).post("/extract/invoice", json={"text": "Invoice INV-1 total $1,200.50"})
    assert response.status_code == 200
    assert response.json()["invoice_number"] == "INV-1"
    assert response.json()["total_amount"] == 1200.5


def test_empty_input_is_rejected_without_llm(monkeypatch):
    def fail_if_called(_):
        raise AssertionError("LLM must not be called for empty input")

    monkeypatch.setattr("app.main.extract_resume", fail_if_called)
    response = TestClient(app).post("/extract/resume", json={"text": "  \n"})
    assert response.status_code == 400
    assert "must not be empty" in response.json()["detail"]


def test_too_long_input_is_rejected(monkeypatch):
    monkeypatch.setenv("MAX_INPUT_CHARS", "3")
    response = TestClient(app).post("/extract/resume", json={"text": "four"})
    assert response.status_code == 413


def test_missing_fields_have_nulls_or_empty_lists(monkeypatch):
    expected = ResumeData(name="")
    monkeypatch.setattr("app.main.extract_resume", lambda _: expected)
    response = TestClient(app).post("/extract/resume", json={"text": "random text"})
    assert response.status_code == 200
    assert response.json()["name"] == ""
    assert response.json()["email"] is None
    assert response.json()["skills"] == []


def test_misconfigured_provider_returns_safe_server_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    response = TestClient(app).post("/extract/resume", json={"text": "Jane Doe"})
    assert response.status_code == 500
    assert "Unsupported LLM_PROVIDER" in response.json()["detail"]


def test_invalid_llm_structure_returns_validation_details(monkeypatch):
    from pydantic import ValidationError

    def invalid_result(_):
        raise ValidationError.from_exception_data(
            "ResumeData",
            [{"type": "string_type", "loc": ("name",), "input": 42}],
        )

    monkeypatch.setattr("app.main.extract_resume", invalid_result)
    response = TestClient(app).post("/extract/resume", json={"text": "Jane Doe"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["name"]
