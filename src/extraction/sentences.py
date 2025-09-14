from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import re, unicodedata, hashlib

# Abbreviation list (no variable-width lookbehind; we check in Python code)
_ABBR = r"(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|Mt|vs|No|Inc|Ltd|Fig|Eq|Ref|et al|i\.e|e\.g|cf|Ph\.D|M\.Sc|U\.S|U\.K)"
_ABBR_WORD_RE = re.compile(rf"^{_ABBR}$", re.IGNORECASE)

# Find candidate sentence boundaries: ".", "!", or "?" + whitespace + a likely sentence starter
# (capital letter or opening quote/paren). No look-behind.
_SENT_END_RE = re.compile(r"[\.!?]\s+(?=[A-Z(“\"'])")

@dataclass
class SentRecord:
    id: str
    page: int
    text: str
    bbox: Tuple[float, float, float, float]
    page_char_start: int
    page_char_end: int
    global_char_start: int
    global_char_end: int
    hash16: str

def _line_text(line: Dict[str, Any]) -> str:
    return "".join(sp.get("text", "") for sp in line.get("spans", [])).strip()

def _line_bbox(line: Dict[str, Any]) -> Tuple[float, float, float, float]:
    ys = [sp["bbox"][1] for sp in line["spans"]] + [sp["bbox"][3] for sp in line["spans"]]
    xs = [sp["bbox"][0] for sp in line["spans"]] + [sp["bbox"][2] for sp in line["spans"]]
    return (min(xs), min(ys), max(xs), max(ys))

def _norm_for_hash(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = " ".join(s.split())  # collapse whitespace
    return s.lower()

def _hash16(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

def _bbox_for_span(line_bboxes: List[Tuple[int,int,float,float,float,float]], span_start: int, span_end: int):
    xs0, ys0, xs1, ys1 = [], [], [], []
    for (ls, le, x0, y0, x1, y1) in line_bboxes:
        if not (span_end <= ls or span_start >= le):  # overlaps
            xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
    if not xs0:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs0), min(ys0), max(xs1), max(ys1))

def _is_abbrev_before(text: str, punct_pos: int) -> bool:
    """
    Given the full page text and the index of the sentence-ending punctuation,
    check if the token right before that punctuation is an abbreviation (e.g., "Dr.", "e.g.").
    """
    # Look back a bit to find the preceding token (letters, dots)
    start_scan = max(0, punct_pos - 25)
    chunk = text[start_scan:punct_pos]  # up to the punctuation
    # Extract the last 'word' containing letters/dots
    m = re.search(r"([A-Za-z\.]+)$", chunk)
    if not m:
        return False
    word = m.group(1)
    # Many abbreviations include a trailing dot; we check both "Dr" and "Dr." style
    word_no_dot = word[:-1] if word.endswith(".") else word
    if _ABBR_WORD_RE.match(word) or _ABBR_WORD_RE.match(word_no_dot):
        return True
    return False

def iter_page_sentences(doc, pno: int, global_cursor: int) -> Tuple[List[SentRecord], int, str]:
    """
    Returns (records, new_global_cursor, reconstructed_page_text).
    Records have deterministic ids: S{page:03d}-{index:05d}
    """
    blocks = doc[pno].get_text("dict").get("blocks", [])
    page_frags: List[str] = []
    line_bboxes: List[Tuple[int,int,float,float,float,float]] = []
    cursor = 0

    # Reconstruct page text with line mapping
    for b in blocks:
        if "lines" not in b:
            continue
        for ln in b["lines"]:
            t = _line_text(ln)
            if not t:
                continue
            t = unicodedata.normalize("NFKC", t)
            x0,y0,x1,y1 = _line_bbox(ln)
            page_frags.append(t)
            start_idx = cursor
            cursor += len(t)
            end_idx = cursor
            line_bboxes.append((start_idx, end_idx, x0, y0, x1, y1))
            page_frags.append("\n")
            cursor += 1

    page_text = "".join(page_frags)
    page_len = len(page_text)

    recs: List[SentRecord] = []
    start = 0
    local_idx = 0

    def add_span(span_start: int, span_end: int):
        nonlocal local_idx
        chunk = page_text[span_start:span_end].strip()
        if not chunk:
            return
        bbox = _bbox_for_span(line_bboxes, span_start, span_end)
        local_idx += 1
        sid = f"S{pno+1:03d}-{local_idx:05d}"
        h16 = _hash16(_norm_for_hash(chunk))
        recs.append(SentRecord(
            id=sid,
            page=pno+1,
            text=chunk,
            bbox=bbox,
            page_char_start=span_start,
            page_char_end=span_end,
            global_char_start=global_cursor + span_start,
            global_char_end=global_cursor + span_end,
            hash16=h16
        ))

    # Scan for sentence boundaries; skip split if abbreviation lies before punctuation
    for m in _SENT_END_RE.finditer(page_text):
        # punctuation is the char just before the space(s)
        punct_pos = m.start()  # index of the punctuation char (.,!,?)
        if _is_abbrev_before(page_text, punct_pos):
            continue
        add_span(start, punct_pos + 1)  # include the punctuation in the sentence
        start = m.end()

    # Tail after last match
    if start < page_len:
        add_span(start, page_len)

    # Advance global cursor by page length + the extra newline we add between pages in full.txt
    new_global_cursor = global_cursor + page_len + 2
    return recs, new_global_cursor, page_text
