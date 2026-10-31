import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.config import get_settings
from app.extractor import (
    ExtractionRateLimitError,
    ExtractionUnavailableError,
    extract_invoice,
    extract_resume,
)
from app.llm import LLMConfigurationError, validate_provider_configuration
from app.schemas import InvoiceData, ResumeData, TextRequest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configuration_error = validate_provider_configuration()
    if configuration_error:
        logger.warning("LLM configuration issue: %s", configuration_error)
    yield


app = FastAPI(
    title="Data Extraction Bot",
    description="Extract validated resume and invoice data from unstructured text.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "provider": settings.llm_provider, "model": settings.llm_model or "not configured"}


def _check_input(text: str) -> None:
    if not text.strip():
        raise HTTPException(status_code=400, detail="Input text must not be empty or whitespace-only.")
    if len(text) > get_settings().max_input_chars:
        raise HTTPException(status_code=413, detail="Input text exceeds the maximum allowed length.")


def _extract(text: str, extractor):
    try:
        return extractor(text)
    except LLMConfigurationError as error:
        logger.warning("LLM configuration prevented extraction: %s", error)
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ExtractionRateLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except ExtractionUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors(include_url=False)) from error


@app.post("/extract/resume", response_model=ResumeData)
def resume(request: TextRequest) -> ResumeData:
    _check_input(request.text)
    return _extract(request.text, extract_resume)


@app.post("/extract/invoice", response_model=InvoiceData)
def invoice(request: TextRequest) -> InvoiceData:
    _check_input(request.text)
    return _extract(request.text, extract_invoice)
