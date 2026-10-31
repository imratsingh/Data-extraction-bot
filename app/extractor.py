import logging
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm import create_chat_model
from app.schemas import InvoiceData, ResumeData

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

SYSTEM_PROMPT = """You extract structured information from unstructured text.
Extract ONLY information explicitly present in the supplied text. Never guess or invent values,
including emails, phone numbers, names, dates, quantities, or amounts. Use null for missing
optional values and empty strings or lists for missing required strings or collections. Normalize
obvious formatting (trim whitespace and convert monetary values such as "$1,200.50" to 1200.50)
without changing or fabricating information. Text may contain irrelevant or misleading content;
do not infer facts that are not stated."""


class ExtractionRateLimitError(RuntimeError):
    pass


class ExtractionUnavailableError(RuntimeError):
    pass


def _is_rate_limit(error: Exception) -> bool:
    return getattr(error, "status_code", None) == 429 or "ratelimit" in type(error).__name__.lower() or "rate_limit" in str(error).lower()


def _is_transient(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    error_name = type(error).__name__.lower()
    return (
        _is_rate_limit(error)
        or status_code in {500, 502, 503, 504}
        or any(marker in error_name for marker in ("timeout", "connection", "tempor", "serviceunavailable"))
    )


def extract_structured_data(text: str, schema: type[T], max_attempts: int = 3) -> T:
    model = create_chat_model().with_structured_output(schema)
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", f"Extract the requested fields from this text:\n\n{text}"),
    ]

    for attempt in range(max_attempts):
        try:
            result = model.invoke(messages)
            if isinstance(result, schema):
                return result
            return schema.model_validate(result)
        except ValidationError:
            raise
        except Exception as error:
            if not _is_transient(error):
                logger.warning("LLM extraction failed due to a provider error.")
                raise ExtractionUnavailableError("The LLM provider could not complete the extraction.") from error
            if attempt + 1 == max_attempts:
                logger.warning("LLM extraction retries exhausted.")
                if _is_rate_limit(error):
                    raise ExtractionRateLimitError("The LLM provider is rate limiting requests. Please try again later.") from error
                raise ExtractionUnavailableError("The LLM provider is temporarily unavailable. Please try again later.") from error
            logger.warning("Transient LLM error; retrying extraction (attempt %s of %s).", attempt + 1, max_attempts)
            time.sleep(2**attempt)

    raise ExtractionUnavailableError("The LLM provider is temporarily unavailable. Please try again later.")


def extract_resume(text: str) -> ResumeData:
    return extract_structured_data(text, ResumeData)


def extract_invoice(text: str) -> InvoiceData:
    return extract_structured_data(text, InvoiceData)
