import pytest
from pydantic import ValidationError

from app import extractor
from app.schemas import InvoiceData, ResumeData


class FakeStructuredModel:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return output


class FakeChatModel:
    def __init__(self, structured_model):
        self.structured_model = structured_model

    def with_structured_output(self, _schema):
        return self.structured_model


def test_structured_resume_extraction(monkeypatch):
    expected = ResumeData(name="Jane Doe", skills=["Python"])
    structured = FakeStructuredModel([expected])
    monkeypatch.setattr(extractor, "create_chat_model", lambda: FakeChatModel(structured))
    result = extractor.extract_resume("Jane Doe knows Python")
    assert result == expected


def test_structured_invoice_extraction(monkeypatch):
    structured = FakeStructuredModel([{"total_amount": 1200.5, "currency": "USD"}])
    monkeypatch.setattr(extractor, "create_chat_model", lambda: FakeChatModel(structured))
    result = extractor.extract_invoice("Total: $1,200.50")
    assert result.total_amount == 1200.5


def test_transient_error_retries_up_to_three_attempts(monkeypatch):
    structured = FakeStructuredModel([TimeoutError("temporary"), TimeoutError("temporary"), {"name": "A"}])
    monkeypatch.setattr(extractor, "create_chat_model", lambda: FakeChatModel(structured))
    monkeypatch.setattr(extractor.time, "sleep", lambda _: None)
    assert extractor.extract_resume("A").name == "A"
    assert structured.calls == 3


def test_rate_limit_after_retries_has_helpful_error(monkeypatch):
    class RateLimitError(Exception):
        status_code = 429

    structured = FakeStructuredModel([RateLimitError("slow down")] * 3)
    monkeypatch.setattr(extractor, "create_chat_model", lambda: FakeChatModel(structured))
    monkeypatch.setattr(extractor.time, "sleep", lambda _: None)
    with pytest.raises(extractor.ExtractionRateLimitError, match="rate limiting"):
        extractor.extract_invoice("invoice")
    assert structured.calls == 3


def test_invalid_structure_raises_validation_error(monkeypatch):
    structured = FakeStructuredModel([{"name": 3}])
    monkeypatch.setattr(extractor, "create_chat_model", lambda: FakeChatModel(structured))
    with pytest.raises(ValidationError):
        extractor.extract_resume("some text")
