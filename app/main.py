import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.config import get_settings
from app.extractor import (
    ExtractionRateLimitError,
    ExtractionUnavailableError,
    extract_invoice,
    extract_resume,
)
from app.llm import LLMConfigurationError, validate_provider_configuration
from app.pdf import InvalidPDFError, PDFHasNoTextError, UnsupportedPDFError, extract_pdf_text
from app.schemas import InvoiceData, ResumeData, TextRequest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
MAX_PDF_BYTES = 10 * 1024 * 1024


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


async def _extract_pdf(file: UploadFile, extractor):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    content = await file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the 10 MB file size limit.")

    try:
        text = extract_pdf_text(content)
    except InvalidPDFError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (PDFHasNoTextError, UnsupportedPDFError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    _check_input(text)
    return _extract(text, extractor)


@app.post("/extract/resume/pdf", response_model=ResumeData)
async def resume_pdf(file: UploadFile = File(...)) -> ResumeData:
    return await _extract_pdf(file, extract_resume)


@app.post("/extract/invoice/pdf", response_model=InvoiceData)
async def invoice_pdf(file: UploadFile = File(...)) -> InvoiceData:
    return await _extract_pdf(file, extract_invoice)


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="frontend")
