from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class InvalidPDFError(ValueError):
    pass


class UnsupportedPDFError(ValueError):
    pass


class PDFHasNoTextError(ValueError):
    pass


def extract_pdf_text(content: bytes) -> str:
    if b"%PDF-" not in content[:1024]:
        raise InvalidPDFError("The uploaded file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise UnsupportedPDFError("This PDF is password-protected. Upload an unlocked PDF.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except PdfReadError as error:
        raise InvalidPDFError("The PDF could not be read. Try exporting it again and re-uploading.") from error

    if not text.strip():
        raise PDFHasNoTextError(
            "No selectable text was found in this PDF. Scanned documents need OCR before upload."
        )
    return text
