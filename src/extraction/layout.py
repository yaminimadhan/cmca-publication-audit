# src/extraction/layout.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import re, unicodedata

@dataclass
class Heading:
    title: str
    pno: int
    y0: float
    y1: float

def _avg_font_size(blocks: List[Dict[str, Any]]) -> float:
    sizes = []
    for b in blocks:
        if "lines" not in b:
            continue
        for ln in b["lines"]:
            for sp in ln["spans"]:
                sizes.append(sp.get("size", 0.0))
    return (sum(sizes) / len(sizes)) if sizes else 10.0

def _line_text(line: Dict[str, Any]) -> str:
    return "".join(sp.get("text", "") for sp in line.get("spans", [])).strip()

def _line_bbox(line: Dict[str, Any]) -> Tuple[float, float, float, float]:
    ys = [sp["bbox"][1] for sp in line["spans"]] + [sp["bbox"][3] for sp in line["spans"]]
    xs = [sp["bbox"][0] for sp in line["spans"]] + [sp["bbox"][2] for sp in line["spans"]]
    return (min(xs), min(ys), max(xs), max(ys))

def _is_heading(text: str, spans: List[Dict[str, Any]], avg_font: float) -> bool:
    clean = unicodedata.normalize("NFKC", text).strip()
    if not clean or len(clean) > 120:
        return False
    # mostly alphabetic
    alnum = sum(ch.isalpha() for ch in clean)
    if alnum < 0.6 * len(clean.replace(" ", "")):
        return False
    big = any(s.get("size", 0.0) >= avg_font * 1.2 for s in spans)
    boldish = any(("Bold" in s.get("font", "") or "Semibold" in s.get("font", "")) for s in spans)
    caps_or_title = (clean.isupper() or re.match(r"^[A-Z][A-Za-z0-9 ,–—\-:;()]+$", clean) is not None)
    shortish = len(clean.split()) <= 10
    return (big or boldish) and caps_or_title and shortish

def detect_headings(blocks_by_page: List[List[dict]]) -> List[Heading]:
    """Detect heading lines across pages using visual cues only."""
    heads: List[Heading] = []
    for pno, blocks in enumerate(blocks_by_page):
        avg_font = _avg_font_size(blocks)
        for b in blocks:
            if "lines" not in b:
                continue
            for ln in b["lines"]:
                text = _line_text(ln)
                if not text:
                    continue
                if _is_heading(text, ln.get("spans", []), avg_font):
                    x0, y0, x1, y1 = _line_bbox(ln)
                    heads.append(Heading(title=text.strip(), pno=pno, y0=y0, y1=y1))

    heads.sort(key=lambda h: (h.pno, h.y0))

    # de-dup consecutive identical titles on the same page (sometimes extracted twice)
    dedup: List[Heading] = []
    for h in heads:
        if dedup and h.title == dedup[-1].title and h.pno == dedup[-1].pno and abs(h.y0 - dedup[-1].y0) < 2:
            continue
        dedup.append(h)
    return dedup

def segment_by_headings(doc, page_texts: List[str], headings: List[Heading]) -> List[dict]:
    """
    Create {title, content} segments by cutting from each heading to the next heading (by page/y).
    Uses per-line y-bounds to trim within the first and last pages of a segment.
    """
    if not headings:
        return [{"title": "DOCUMENT", "content": "\n".join(page_texts).strip()}]

    segments: List[Dict[str, str]] = []
    blocks_cache = [doc[p].get_text("dict") for p in range(len(page_texts))]

    for i, h in enumerate(headings):
        end_p = headings[i + 1].pno if i + 1 < len(headings) else len(page_texts) - 1
        end_y = headings[i + 1].y0 if i + 1 < len(headings) else None

        buf_lines: List[str] = []
        for p in range(h.pno, end_p + 1):
            if p == h.pno or (end_y is not None and p == end_p):
                blocks = blocks_cache[p]
                page_lines = []
                for b in blocks.get("blocks", []):
                    if "lines" not in b:
                        continue
                    for ln in b["lines"]:
                        y0 = min(sp["bbox"][1] for sp in ln["spans"])
                        txt = _line_text(ln)
                        if not txt:
                            continue
                        if p == h.pno and y0 <= h.y1:
                            continue  # skip heading line and anything above it
                        if end_y is not None and p == end_p and y0 >= end_y:
                            continue  # stop before next heading line
                        page_lines.append(txt)
                buf_lines.append("\n".join(page_lines))
            else:
                buf_lines.append(page_texts[p])

        content = "\n".join(buf_lines).strip()
        segments.append({"title": h.title, "content": content})

    return segments
