#!/usr/bin/env python3
"""
Research PDF → text (page + sentence level) + minimal metadata (6 keys)

Outputs in --outdir:
  - pages.jsonl         : {"page": int, "text": str}
  - sentences.jsonl     : {"id": "p{page}_s{index}", "page": int, "index": int, "text": str}
  - fulltext.txt        : full document with clear page breaks
  - metadata.json       : {title, authors, doi, year, instruments, pages}
"""

from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Use PyMuPDF for reliable layout extraction (no OCR)
try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise SystemExit("PyMuPDF is required. Install with: pip install pymupdf") from e


# ------------------------------- Utilities -------------------------------

def norm_ws(s: str) -> str:
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------- Layout handling ----------------------------

def page_blocks_sorted(page) -> List[Tuple[float, float, float, float, str]]:
    """
    Return blocks [(x0,y0,x1,y1,text)] sorted primarily by top (y0), then left (x0).
    """
    blocks = []
    for b in page.get_text("blocks") or []:
        if len(b) >= 5:
            x0, y0, x1, y1, txt = b[:5]
            if isinstance(txt, str) and txt.strip():
                blocks.append((float(x0), float(y0), float(x1), float(y1), txt))
    blocks.sort(key=lambda t: (round(t[1], 1), round(t[0], 1)))
    return blocks

def guess_column_centers(x_lefts: List[float]) -> List[float]:
    """
    Tiny gap-based splitter of left-edge x positions.
    Returns 1 or 2 cluster centers (for 1- or 2-column pages).
    """
    if not x_lefts:
        return []
    xs = sorted(x_lefts)
    gaps = [(xs[i+1] - xs[i], i) for i in range(len(xs)-1)]
    if not gaps:
        return [sum(xs)/len(xs)]
    biggest_gap, idx = max(gaps)
    # If the biggest gap is prominent enough, assume two columns
    if biggest_gap > 40:  # tweak threshold if needed
        left = xs[:idx+1]; right = xs[idx+1:]
        return [sum(left)/len(left), sum(right)/len(right)]
    return [sum(xs)/len(xs)]

def merge_blocks_reading_order(blocks: List[Tuple[float,float,float,float,str]]) -> str:
    """
    Merge block texts in reading order. If two columns are detected:
    read entire left column top→bottom, then right column top→bottom.
    """
    if not blocks:
        return ""
    x_lefts = [b[0] for b in blocks]
    centers = guess_column_centers(x_lefts)
    # single column
    if len(centers) == 1:
        return "\n".join(norm_ws(b[4]) for b in blocks).strip()

    # two columns
    c_left, c_right = sorted(centers)
    split_x = (c_left + c_right)/2.0
    left_blocks = [b for b in blocks if b[0] <= split_x]
    right_blocks = [b for b in blocks if b[0] > split_x]
    left_blocks.sort(key=lambda t: (round(t[1],1), round(t[0],1)))
    right_blocks.sort(key=lambda t: (round(t[1],1), round(t[0],1)))

    left_text = "\n".join(norm_ws(b[4]) for b in left_blocks)
    right_text = "\n".join(norm_ws(b[4]) for b in right_blocks)
    return (left_text + "\n\n" + right_text).strip()


# --------------------------- Metadata heuristics --------------------------

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

def extract_title_and_authors(doc) -> Tuple[Optional[str], List[str]]:
    """
    Heuristic title (largest spans near top) and authors (spans just below title).
    Works well on many publisher PDFs; not guaranteed.
    """
    try:
        page0 = doc.load_page(0)
        d = page0.get_text("dict")
    except Exception:
        return None, []

    spans = []
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            y = float(line.get("bbox", [0,0,0,0])[1])
            for span in line.get("spans", []):
                txt = (span.get("text") or "").strip()
                if not txt:
                    continue
                size = float(span.get("size", 0.0))
                spans.append({"text": txt, "size": size, "y": y})

    if not spans:
        return None, []

    max_size = max(s["size"] for s in spans)
    title_lines = [s for s in spans if abs(s["size"] - max_size) < 0.2 and s["y"] < 0.35*page0.rect.height]
    title = None
    if title_lines:
        title = " ".join(s["text"] for s in sorted(title_lines, key=lambda s: s["y"]))
        title = re.sub(r"\s{2,}", " ", title).strip(" .–-:")

    authors: List[str] = []
    if title_lines:
        band_top = max(s["y"] for s in title_lines)
        band = [s for s in spans if band_top < s["y"] < band_top + 220]  # ~220px after title
        candidate = " ".join(s["text"] for s in sorted(band, key=lambda s: s["y"]))
        candidate = re.sub(r"[\*\d†‡§#]+", "", candidate)  # strip markers
        parts = re.split(r"\s*(?:,|;| and )\s*", candidate)
        for p in parts:
            p = p.strip()
            if not p or "@" in p:
                continue
            # Keep shortish tokens (avoid affiliations)
            if 2 <= len(p.split()) <= 5:
                authors.append(p)
        # de-dup keep order
        seen=set(); authors = [a for a in authors if not (a.lower() in seen or seen.add(a.lower()))]

    return (title if title else None, authors)

INSTRUMENT_KEYWORDS = [
    # techniques
    "SEM","TEM","AFM","XRD","X-ray diffraction","NMR","FTIR","Raman","LC-MS","GC-MS","HPLC",
    # common vendors/brands
    "Zeiss","Rigaku","Bruker","JEOL","Thermo Fisher","Hitachi","Nikon","Oxford Instruments","Micromeritics","Gatan","Asylum Research"
]

def detect_instruments(text: str) -> List[str]:
    found = []
    for kw in INSTRUMENT_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text, re.I):
            found.append(kw)
    # normalize “X-ray diffraction” → “XRD” if both appear (keep unique, readable)
    uniq = []
    for k in found:
        if k not in uniq:
            uniq.append(k)
    return uniq


# ------------------------- Sentence segmentation --------------------------

# Simple, practical splitter with abbreviation guard
_ABBREV = set([
    "e.g.", "i.e.", "et al.", "Fig.", "Figs.", "Eq.", "Eqs.", "Dr.", "Mr.", "Ms.", "Prof.", "vs.", "No.", "ca.", "cf."
])

def split_into_sentences(text: str) -> List[str]:
    """
    Lightweight sentence splitter: split on [.?!] + space + capital/paren, but keep common abbreviations together.
    """
    if not text:
        return []
    # Normalize weird line breaks inside paragraphs
    t = re.sub(r"\s+\n\s+", " ", text)
    # Token-based pass
    parts = re.split(r"(?<=[\.\?\!])\s+(?=[A-Z(])", t)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Merge if this fragment looks like an orphaned abbrev tail
        if out and any(p.startswith(x.replace(".", "")) for x in ["et al", "e.g", "i.e"]):
            out[-1] = (out[-1] + " " + p).strip()
        else:
            out.append(p)
    # Join accidental splits after abbreviations
    fixed = []
    for s in out:
        if fixed and any(fixed[-1].endswith(a) for a in _ABBREV):
            fixed[-1] = (fixed[-1] + " " + s).strip()
        else:
            fixed.append(s)
    # Remove very short noise
    return [s.strip() for s in fixed if len(s.strip()) > 1]


# --------------------------------- Core ----------------------------------

def extract(pdf_path: Path, outdir: Path) -> None:
    doc = fitz.open(str(pdf_path))
    page_texts: List[str] = []
    sentences_rows: List[Dict[str, Any]] = []

    # Per-page: build reading-ordered text (handles 1 or 2 columns)
    for i in range(len(doc)):
        page = doc.load_page(i)
        blocks = page_blocks_sorted(page)
        text = merge_blocks_reading_order(blocks)
        text = norm_ws(text)
        page_texts.append(text)

        # Sentence rows with stable IDs per page
        sents = split_into_sentences(text)
        for idx, s in enumerate(sents, start=1):
            sentences_rows.append({
                "id": f"p{i+1}_s{idx}",
                "page": i+1,
                "index": idx,
                "text": s
            })

    # Write outputs
    outdir.mkdir(parents=True, exist_ok=True)

    # pages.jsonl
    write_jsonl(outdir / "pages.jsonl", [{"page": i+1, "text": t} for i, t in enumerate(page_texts)])

    # sentences.jsonl
    write_jsonl(outdir / "sentences.jsonl", sentences_rows)

    # fulltext.txt
    (outdir / "fulltext.txt").write_text(
        "\n\n==== PAGE BREAK ====\n\n".join(page_texts), encoding="utf-8"
    )

    # Metadata (exactly 6 keys)
    first_two = "\n".join(page_texts[:2])
    full_text = "\n".join(page_texts)

    doi_m = DOI_RE.search(first_two) or DOI_RE.search(full_text)
    doi = doi_m.group(1) if doi_m else None

    year = None
    for scope in (first_two, full_text):
        m = YEAR_RE.search(scope)
        if m:
            year = m.group(0); break

    title, authors = extract_title_and_authors(doc)
    instruments = detect_instruments(full_text)

    metadata = {
        "title": title,
        "authors": authors,
        "doi": doi,
        "year": year,
        "instruments": instruments,
        "pages": len(doc),
    }
    write_json(outdir / "metadata.json", metadata)

    # Console summary
    print(f"✅ {pdf_path.name}: {len(doc)} pages")
    print(f"Title: {title}")
    print(f"Authors: {', '.join(authors) if authors else '—'}")
    print(f"DOI: {doi or '—'} | Year: {year or '—'} | Instruments: {', '.join(instruments) if instruments else '—'}")
    print(f"Sentences: {len(sentences_rows)} (see sentences.jsonl)")


# --------------------------------- CLI -----------------------------------

def main():
    ap = argparse.ArgumentParser(description="Extract clean text (page + sentences) and 6-field metadata from a research PDF.")
    ap.add_argument("pdf", type=str, help="Path to PDF file")
    ap.add_argument("-o", "--outdir", type=str, default="out", help="Output folder")
    args = ap.parse_args()

    extract(Path(args.pdf), Path(args.outdir))

if __name__ == "__main__":
    main()
