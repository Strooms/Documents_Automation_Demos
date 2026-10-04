"""Text acquisition: PDF text layer first, Tesseract OCR as a fallback."""
from __future__ import annotations

import io
import shutil
from typing import Tuple

import pdfplumber

MIN_TEXT_CHARS = 30  # fewer characters than this on a page => treat the page as image-only


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _ocr_pdf(path: str, dpi: int = 300) -> str:
    import pymupdf  # imported lazily so text-only use does not need it
    import pytesseract
    from PIL import Image

    pages = []
    with pymupdf.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            # --psm 6: assume a uniform block of text; keeps table rows on one line.
            pages.append(pytesseract.image_to_string(image, config="--psm 6"))
    return "\n".join(pages)


def read_pdf_text(path: str) -> Tuple[str, str]:
    """Return (text, method) where method is 'text' or 'ocr'.

    Raises RuntimeError if the PDF has no text layer and Tesseract is not installed.
    """
    with pdfplumber.open(path) as pdf:
        texts = [(page.extract_text() or "") for page in pdf.pages]
    if all(len(t.strip()) >= MIN_TEXT_CHARS for t in texts):
        return "\n".join(texts), "text"
    if not tesseract_available():
        raise RuntimeError(
            f"{path}: no text layer and Tesseract is not installed "
            "(install it, e.g. `sudo apt-get install tesseract-ocr`)."
        )
    return _ocr_pdf(path), "ocr"
