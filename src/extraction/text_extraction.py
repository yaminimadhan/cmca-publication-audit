from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF

def extract_pages_text(pdf_path: Path) -> Tuple[List[str], fitz.Document]:
    """Return per-page plain text and an open PyMuPDF Document (caller must close)."""
    doc = fitz.open(str(pdf_path))
    pages: List[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    return pages, doc

def page_blocks_dict(doc: fitz.Document, pno: int) -> dict:
    """Return the 'dict' structure with spans / geometry for a page."""
    return doc[pno].get_text("dict")
