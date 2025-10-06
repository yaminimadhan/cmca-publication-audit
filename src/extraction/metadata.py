from __future__ import annotations
import re
from typing import Dict, List

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", re.I)

INSTRUMENT_KEYWORDS = [
    "SEM","TEM","EDX","EDS","ICP-OES","ICP-MS","NMR","PFG","XRD","SAXS","WAXS",
    "spectrometer","microscope","microscopy","spectroscopy","diffraction"
]

def extract_metadata(doc, fulltext: str) -> Dict:
    meta = doc.metadata or {}
    title = meta.get("title") or None
    author_raw = meta.get("author") or None
    doi = None
    m = DOI_RE.search(fulltext)
    if m:
        doi = m.group(1)
    year = None
    ym = re.search(r"\b(20\d{2})\b", fulltext)
    if ym:
        year = ym.group(1)
    return {"title": title, "author_raw": author_raw, "doi": doi, "year": year}

def detect_instruments(text: str) -> List[str]:
    found = []
    for kw in INSTRUMENT_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", text, re.I):
            found.append(kw)
    # de-dup, order-preserving
    seen = set()
    out = []
    for k in found:
        kl = k.lower()
        if kl not in seen:
            seen.add(kl)
            out.append(k)
    return out
