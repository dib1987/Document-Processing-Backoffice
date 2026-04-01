"""
OCR Service — extracts text from uploaded documents.

Strategy:
1. For PDFs: try PyMuPDF native text extraction first (fast, accurate for digital PDFs).
   If text density < threshold (scanned/image-based PDF), fall back to OCR.
2. For images (JPG, PNG, TIFF, BMP): always use pytesseract OCR.

Returns: (full_text: str, page_count: int)
"""
import io
import os

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageFilter, ImageOps

from config import get_settings

settings = get_settings()

if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}
PDF_EXTENSION = ".pdf"


def extract_text(file_bytes: bytes, filename: str) -> tuple[str, int]:
    """
    Extract text from document bytes.
    Returns (full_text, page_count).
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == PDF_EXTENSION:
        return _extract_from_pdf(file_bytes)
    elif ext in IMAGE_EXTENSIONS:
        text = _ocr_image_bytes(file_bytes)
        return text, 1
    else:
        # Try PDF path as fallback for unknown types
        try:
            return _extract_from_pdf(file_bytes)
        except Exception:
            return "", 0


def _extract_from_pdf(file_bytes: bytes) -> tuple[str, int]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page_count = len(doc)

    # Try native text extraction
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())

    native_text = "\n".join(pages_text)
    avg_chars_per_page = len(native_text) / max(page_count, 1)

    if avg_chars_per_page >= settings.ocr_text_density_threshold:
        # Digital PDF — native text is reliable
        doc.close()
        return _normalize_whitespace(native_text), page_count

    # Scanned/image PDF — render each page and OCR it
    ocr_pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")
        ocr_pages.append(_ocr_image_bytes(img_bytes))

    doc.close()
    return _normalize_whitespace("\n".join(ocr_pages)), page_count


def _ocr_image_bytes(image_bytes: bytes) -> str:
    """Run pytesseract on raw image bytes with preprocessing."""
    img = Image.open(io.BytesIO(image_bytes))
    img = _preprocess_image(img)
    text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")
    return text


def _preprocess_image(img: Image.Image) -> Image.Image:
    """
    Improve OCR accuracy:
    - Convert to grayscale (removes color noise)
    - Auto-contrast (normalizes brightness)
    - Sharpen (improves edge definition for OCR)
    """
    img = img.convert("L")          # Grayscale
    img = ImageOps.autocontrast(img)  # Normalize contrast
    img = img.filter(ImageFilter.SHARPEN)
    return img


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple blank lines, strip trailing spaces."""
    lines = [line.rstrip() for line in text.splitlines()]
    # Collapse 3+ consecutive blank lines to 2
    result = []
    blank_count = 0
    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result).strip()
