import fitz
import spacy, re
from collections import Counter
from pathlib import Path



pdf_path = "sample.pdf"
out_dir  = Path("output")
min_chars = 40
LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl",
    "\u00ad": "",
}

def normalize_text(s: str) -> str:
    for k, v in LIGATURES.items():
        s = s.replace(k, v)
    s = s.replace("\u00A0", " ")              
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()

def dehyphenate(text: str) -> str:
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    return text

def learn_common_edges(doc):
    """Find repeated first/last lines across pages (headers/footers)."""
    first_lines, last_lines = [], []
    for page in doc:
        raw = page.get_text("text") or ""
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if lines:
            first_lines.append(lines[0])
            last_lines.append(lines[-1])
    thr = max(3, len(doc)//4 or 1)
    common_first = {s for s, c in Counter(first_lines).items() if c >= thr}
    common_last  = {s for s, c in Counter(last_lines).items() if c >= thr}
    return common_first, common_last

def detect_two_columns(page, blocks, min_group=4, gap_frac=0.18):
    if not blocks:
        return False, None
    x0, y0, x1, y1 = page.rect
    page_w = x1 - x0
    centers = [ (b[0]+b[2])/2 for b in blocks ]
    med = sorted(centers)[len(centers)//2]
    left  = [b for b,c in zip(blocks, centers) if c <= med]
    right = [b for b,c in zip(blocks, centers) if c  > med]
    if len(left) < min_group or len(right) < min_group:
        return False, med
    cx_left  = sum((b[0]+b[2])/2 for b in left)/len(left)
    cx_right = sum((b[0]+b[2])/2 for b in right)/len(right)
    sep = abs(cx_right - cx_left)/page_w
    return (sep >= gap_frac), med

def sort_blocks_single_col(blocks):
    bs = list(blocks)
    bs.sort(key=lambda b: (b[1], b[0]))  # y0, then x0
    return bs

def sort_blocks_two_col(blocks, median_x):
    enriched = []
    for b in blocks:
        x0,y0,x1,y1,txt = b[:5]
        col = 0 if ((x0+x1)/2) <= median_x else 1
        enriched.append((col, y0, x0, x1, y1, txt))
    enriched.sort(key=lambda t: (t[0], t[1], t[2]))  # by column, then top-left
    # back to (x0,y0,x1,y1,text)
    return [(e[2], e[1], e[3], e[4], e[5]) for e in enriched]

def clean_block_text(text, common_first, common_last, min_chars):
    if not text or text.isspace():
        return ""
    text = normalize_text(text)
    kept = []
    for ln in text.splitlines():
        s = ln.strip()
        if s in common_first or s in common_last:
            continue
        if min_chars and len(s) < min_chars:
            continue
        kept.append(s)
    return "\n".join(kept).strip()


doc = fitz.open(pdf_path)
common_first, common_last = learn_common_edges(doc)
pages_clean = []

for page in doc:
    blocks = page.get_text("blocks") or []
    # detect per-page column layout
    is_two, median_x = detect_two_columns(page, blocks)
    if is_two:
        blocks_sorted = sort_blocks_two_col(blocks, median_x)
    else:
        blocks_sorted = sort_blocks_single_col(blocks)

    parts = []
    for b in blocks_sorted:
        # Each block is (x0,y0,x1,y1,text, ...)
        txt = b[4] if len(b) >= 5 else (b[-1] if b else "")
        cleaned = clean_block_text(txt, common_first, common_last, min_chars)
        if cleaned:
            parts.append(cleaned)
    page_txt = "\n".join(parts)
    page_txt = dehyphenate(page_txt)
    pages_clean.append(page_txt)

doc.close()

full_text = "\n\n".join([t for t in pages_clean if t])

nlp = spacy.blank("en")
if "sentencizer" not in nlp.pipe_names:
    nlp.add_pipe("sentencizer")
sentences = [s.text.strip() for s in nlp(full_text).sents if s.text.strip()]
sentences = [re.sub(r"\s*-\s*$", "", s) for s in sentences]  # tiny cleanup

out_dir.mkdir(parents=True, exist_ok=True)
base = Path(pdf_path).stem
(Path(out_dir, f"{base}.full_text.txt")).write_text(full_text, encoding="utf-8")
with open(Path(out_dir, f"{base}.sentences.txt"), "w", encoding="utf-8") as f:
    for s in sentences:
        f.write(s + "\n")
with open(Path(out_dir, f"{base}.sentences.jsonl"), "w", encoding="utf-8") as f:
    for s in sentences:
        s_json = '{"sent": "' + s.replace('\\', '\\\\').replace('"', '\\"') + '"}\n'
        f.write(s_json)

print("Done.")
print("Files written to:", out_dir.resolve())
print("\nPreview (first 8 sentences):")
for s in sentences[:8]:
    print("•", s)
