# extract_pdf_text.py
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import List, Dict

import fitz            # PyMuPDF
import pdfplumber      # fallback for tricky PDFs


# --------------------------
# Raw extraction helpers
# --------------------------
def extract_with_pymupdf(pdf_path: Path) -> List[str]:
    pages: List[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            txt = page.get_text("text") or ""
            pages.append(txt)
    return pages

def extract_with_pdfplumber(pdf_path: Path) -> List[str]:
    pages: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            pages.append(txt)
    return pages

def normalize(text: str) -> str:
    # light cleanup only
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


# --------------------------
# Structured extraction
# --------------------------
DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)

SECTION_HEADINGS = [
    # common headings (case-insensitive)
    r"acknowledg(e)?ments?",
    r"funding",
    r"methods?",
    r"materials and methods",
    r"experimental( design| setup)?",
]

INSTRUMENT_KEYWORDS = [
    "microscope", "microscopy", "TEM", "SEM", "STEM", "FIB",
    "cryogenic", "cryo", "spectrometer", "spectroscopy",
    "diffraction", "XRD", "AFM", "confocal", "electron beam"
]

AFFIL_HINTS = [
    "university", "institute", "department", "centre", "center",
    "school", "laboratory", "faculty", "college", "research"
]

def extract_metadata_from_doc(doc: fitz.Document, fulltext: str) -> Dict:
    meta = doc.metadata or {}
    title = meta.get("title") or None
    author_raw = meta.get("author") or None

    doi = None
    m = DOI_RE.search(fulltext)
    if m:
        doi = m.group(1)

    year = None
    ym = re.search(r"\b(20\d{2})\b", fulltext)  # simple year heuristic
    if ym:
        year = ym.group(1)

    return {
        "title": title,
        "author_raw": author_raw,
        "doi": doi,
        "year": year
    }

def slice_by_headings(all_text: str) -> Dict[str, str]:
    """
    Roughly segment big text by headings using regex.
    Returns a dict of heading_name -> section_text (best-effort).
    """
    # Build a combined regex that captures each heading and following content until next heading
    # Headings appear on their own line typically; allow some punctuation.
    pat = r"(?mi)^(?P<h>(?:%s))\s*[:]*\s*$" % "|".join(SECTION_HEADINGS)
    matches = list(re.finditer(pat, all_text))
    sections = {}

    if not matches:
        return sections

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(all_text)
        heading = m.group("h").lower()
        content = all_text[start:end].strip()
        sections[heading] = content

    return sections

def pick_acknowledgements(segmented: Dict[str, str], all_text: str) -> str | None:
    # try segmented result first
    for key in segmented:
        if "acknowledg" in key or "funding" in key:
            txt = segmented[key].strip()
            if txt:
                return txt
    # fallback: short window after "Acknowledg..." keyword
    m = re.search(r"(?is)(acknowledg(e)?ments?.{0,6}\n+)(.+?)(\n[A-Z].{2,}|$)", all_text)
    if m:
        return (m.group(3) or "").strip()
    return None

def pick_methods(segmented: Dict[str, str], all_text: str) -> str | None:
    for key in segmented:
        if "materials and methods" in key or key.startswith("method") or "experimental" in key:
            txt = segmented[key].strip()
            if txt:
                return txt
    # fallback window
    m = re.search(r"(?is)(materials and methods|methods?|experimental( design| setup)?).{0,6}\n+(.+?)(\n[A-Z].{2,}|$)", all_text)
    if m:
        return (m.group(3) or "").strip()
    return None

def detect_instruments(text: str) -> List[str]:
    found = []
    for kw in INSTRUMENT_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", text, re.I):
            found.append(kw)
    # dedupe, preserve order
    seen = set()
    uniq = []
    for k in found:
        if k.lower() not in seen:
            seen.add(k.lower())
            uniq.append(k)
    return uniq

def guess_affiliations(first_page_text: str) -> str | None:
    # Heuristic: grab a slice from the first page if it contains affiliation hints
    if any(re.search(rf"\b{h}\b", first_page_text, re.I) for h in AFFIL_HINTS):
        # Return first ~800 chars to avoid dumping the whole page
        snippet = first_page_text.strip()
        return snippet[:800]
    return None


# --------------------------
# Main
# --------------------------
def main():
    parser = argparse.ArgumentParser(description="Extract raw text + structured sections from a PDF.")
    parser.add_argument("pdf", type=str, help="Path to PDF")
    parser.add_argument("--outdir", type=str, default="output", help="Output directory (default: output)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    outdir = Path(args.outdir)
    if not pdf_path.exists():
        raise SystemExit(f"❌ File not found: {pdf_path}")

    outdir.mkdir(parents=True, exist_ok=True)

    # -------- Raw extraction (primary + fallback) --------
    pages = extract_with_pymupdf(pdf_path)
    if any(not t.strip() for t in pages):
        fb = extract_with_pdfplumber(pdf_path)
        pages = [p if p.strip() else fb_i for p, fb_i in zip(pages, fb)]

    pages = [normalize(t) for t in pages]
    fulltext = "\n\n".join(pages)

    # Save raw outputs
    base = pdf_path.stem
    jsonl_path = outdir / f"{base}.pages.jsonl"
    fulltxt_path = outdir / f"{base}.full.txt"
    meta_path = outdir / f"{base}.meta.json"
    summary_path = outdir / f"{base}.summary.json"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for i, text in enumerate(pages, start=1):
            rec = {"page_number": i, "text": text}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with fulltxt_path.open("w", encoding="utf-8") as f:
        f.write(fulltext)

    # -------- Structured extraction --------
    with fitz.open(pdf_path) as doc:
        metadata = extract_metadata_from_doc(doc, fulltext)

    segmented = slice_by_headings(fulltext)
    acknowledgements = pick_acknowledgements(segmented, fulltext)
    methods = pick_methods(segmented, fulltext)
    instruments = detect_instruments(fulltext)
    affiliations = guess_affiliations(pages[0] if pages else "")

    summary = {
        "file": str(pdf_path),
        "num_pages": len(pages),
        "metadata": metadata,
        "sections": {
            "acknowledgements": acknowledgements,
            "methods": methods,
            "instruments_found": instruments,
            "affiliations_first_page_snippet": affiliations
        }
    }

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Minimal metadata file (separate, if you want just the basics)
    meta_only = {
        "file": str(pdf_path),
        "num_pages": len(pages),
        **metadata
    }
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta_only, f, ensure_ascii=False, indent=2)

    print(f"✅ Done.\n- Raw pages: {jsonl_path}\n- Full text: {fulltxt_path}\n- Metadata:  {meta_path}\n- Summary:   {summary_path}")


if __name__ == "__main__":
    main()
