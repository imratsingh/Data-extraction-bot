import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import InvoiceData, ResumeData


def test_frontend_homepage_and_assets_are_served():
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert "Extractly" in response.text
    assert "Choose your document" in response.text

    assert client.get("/styles.css").status_code == 200
    assert client.get("/app.js").status_code == 200


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


def test_resume_pdf_upload_extracts_text_and_returns_structured_data(monkeypatch):
    expected = ResumeData(name="Jane Doe", email="jane@example.com")
    monkeypatch.setattr("app.main.extract_pdf_text", lambda _: "Jane Doe, jane@example.com")
    monkeypatch.setattr("app.main.extract_resume", lambda text: expected if "Jane Doe" in text else None)

    response = TestClient(app).post(
        "/extract/resume/pdf",
        files={"file": ("resume.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Jane Doe"


def test_pdf_upload_rejects_non_pdf_filename():
    response = TestClient(app).post(
        "/extract/resume/pdf",
        files={"file": ("resume.txt", b"some text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Please upload a PDF file."


def test_pdf_upload_rejects_files_over_size_limit(monkeypatch):
    monkeypatch.setattr("app.main.MAX_PDF_BYTES", 4)
    response = TestClient(app).post(
        "/extract/resume/pdf",
        files={"file": ("resume.pdf", b"12345", "application/pdf")},
    )

    assert response.status_code == 413


def test_pdf_text_extraction_rejects_scanned_document(monkeypatch):
    from app.pdf import PDFHasNoTextError, extract_pdf_text

    class FakeReader:
        is_encrypted = False
        pages = [type("Page", (), {"extract_text": lambda self: ""})()]

    monkeypatch.setattr("app.pdf.PdfReader", lambda _: FakeReader())
    with pytest.raises(PDFHasNoTextError, match="Scanned documents need OCR"):
        extract_pdf_text(b"%PDF-1.4 test")


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
