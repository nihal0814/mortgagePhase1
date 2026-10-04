from datetime import datetime
from pathlib import Path

from models.document import Document

from config import OCR_DPI, TESSERACT_CMD


def _page_text(page_number: int, text: str) -> str:
    return f"--- Page {page_number} ---\n{text.strip()}\n"


def _ocr_image(image):
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR is not installed. Install pytesseract and Tesseract OCR.") from exc
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    try:
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR was not found. Install it on Windows and set TESSERACT_CMD."
        ) from exc


def extract_document_text(document: Document, file_path: Path) -> str:
    if document.content_type == "application/pdf":
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is not installed. Run pip install -r requirements.txt.") from exc
        try:
            with fitz.open(file_path) as pdf:
                if pdf.is_encrypted:
                    if not pdf.authenticate(""):
                        raise RuntimeError("The PDF is encrypted and could not be opened.")
                pages = []
                has_text = False
                for index, page in enumerate(pdf, start=1):
                    text = page.get_text("text")
                    has_text = has_text or bool(text.strip())
                    pages.append(_page_text(index, text))
                if has_text:
                    return "\n".join(pages).strip()
                try:
                    from pdf2image import convert_from_path
                except ImportError as exc:
                    raise RuntimeError(
                        "This scanned PDF needs OCR. Install pdf2image and Tesseract OCR."
                    ) from exc
                try:
                    images = convert_from_path(str(file_path), dpi=OCR_DPI)
                except Exception as exc:
                    raise RuntimeError(
                        "Scanned PDF OCR needs Poppler installed and available on PATH."
                    ) from exc
                return "\n".join(
                    _page_text(index, _ocr_image(image))
                    for index, image in enumerate(images, start=1)
                ).strip()
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("The PDF could not be read or is corrupted.") from exc

    try:
        from PIL import Image
        with Image.open(file_path) as image:
            return _page_text(1, _ocr_image(image)).strip()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError("The image could not be read for OCR.") from exc


def mark_extraction_success(document: Document, text: str) -> None:
    document.extracted_text = text
    document.extraction_status = "Extracted"
    document.extraction_error = None
    document.extracted_at = datetime.utcnow()
