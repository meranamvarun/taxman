"""
PDF text and table extraction.
Primary: pdfplumber. Fallback: Tesseract OCR for scanned pages.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


def extract_text(pdf_path: str | Path, pages: Optional[list[int]] = None) -> tuple[str, bool]:
    """
    Extract text from PDF.
    Returns (text, is_ocr_used).
    """
    import pdfplumber

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    full_text = []
    ocr_used = False

    with pdfplumber.open(path) as pdf:
        page_list = [pdf.pages[i] for i in pages] if pages else pdf.pages
        for page in page_list:
            text = page.extract_text() or ""
            if len(text.strip()) < 50:
                ocr_text = _ocr_page(page)
                if ocr_text:
                    full_text.append(ocr_text)
                    ocr_used = True
                    continue
            full_text.append(text)

    return "\n".join(full_text), ocr_used


def extract_tables(pdf_path: str | Path, pages: Optional[list[int]] = None) -> list[list[list[str]]]:
    """Extract tables from PDF. Returns list of tables, each is list of rows."""
    import pdfplumber

    path = Path(pdf_path)
    all_tables = []

    with pdfplumber.open(path) as pdf:
        page_list = [pdf.pages[i] for i in pages] if pages else pdf.pages
        for page in page_list:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)

    return all_tables


def is_scanned(pdf_path: str | Path) -> bool:
    """Heuristic: if first page has < 50 chars of text, assume scanned."""
    import pdfplumber

    with pdfplumber.open(Path(pdf_path)) as pdf:
        if not pdf.pages:
            return True
        text = pdf.pages[0].extract_text() or ""
        return len(text.strip()) < 50


def _ocr_page(page) -> str:
    """OCR a single pdfplumber page via Tesseract."""
    try:
        import pytesseract
        from PIL import Image
        import io

        img = page.to_image(resolution=300).original
        if not isinstance(img, Image.Image):
            img_bytes = img
            img = Image.open(io.BytesIO(img_bytes))
        return pytesseract.image_to_string(img, lang="eng")
    except Exception as e:
        print(f"  [OCR warning] Could not OCR page: {e}", file=sys.stderr)
        return ""


def pdf_page_count(pdf_path: str | Path) -> int:
    import pdfplumber
    with pdfplumber.open(Path(pdf_path)) as pdf:
        return len(pdf.pages)
