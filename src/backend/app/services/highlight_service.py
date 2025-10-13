# src/backend/app/services/highlight_service.py

import io
import fitz  # PyMuPDF
from typing import List, Dict, Tuple


def highlight_answer_yes_sentences_from_bytes(
    pdf_bytes: bytes,
    sentences: List[Dict],
    llm_outputs: List[Dict],
    highlight_color: Tuple[float, float, float] = (1, 1, 0),  # yellow
) -> bytes:
    """
    Highlights all sentences where llm_response starts with 'Answer: Yes'.

    Returns:
        New PDF bytes with highlights applied.
    """
    # Build lookup: sentence_id -> sentence text and page
    sent_lookup = {s["id"]: s for s in sentences}

    # Filter for 'Answer: Yes' entries
    yes_ids = [
        o["sentence_id"]
        for o in llm_outputs
        if o.get("llm_response", "").strip().startswith("Answer: Yes")
    ]
    if not yes_ids:
        print("No 'Answer: Yes' sentences found — skipping highlights.")
        return pdf_bytes

    # Open PDF from memory
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for sid in yes_ids:
        s = sent_lookup.get(sid)
        if not s:
            print(f"[warn] Sentence ID not in extractor output: {sid}")
            continue

        page_index = s["page"] - 1
        sentence_text = s["text"].strip()

        page = doc[page_index]
        matches = page.search_for(sentence_text)
        if not matches:
            print(f"[warn] Text not found on page {s['page']}: {sentence_text[:60]}...")
            continue

        for rect in matches:
            highlight = page.add_highlight_annot(rect)
            highlight.set_colors(stroke=highlight_color)
            highlight.update()

    # Export updated PDF to bytes
    out_buf = io.BytesIO()
    doc.save(out_buf, garbage=4, deflate=True)
    return out_buf.getvalue()
