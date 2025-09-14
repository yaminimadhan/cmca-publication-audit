from __future__ import annotations
import argparse
from pathlib import Path
import fitz  # PyMuPDF

from .text_extraction import extract_pages_text
from .layout import detect_headings, segment_by_headings
from .metadata import extract_metadata, detect_instruments
from .io_utils import (
    write_pages_jsonl,
    write_full_text,
    write_summary_json,
    write_meta_json,
    write_sentences_jsonl_gz,   # NEW
)
from .sentences import iter_page_sentences  # NEW


def _first_page_snippet(doc: fitz.Document) -> str | None:
    try:
        return doc[0].get_text("text")[:600]
    except Exception:
        return None


def run_extract(pdf_path: Path, outdir: Path | None = None) -> None:
    outdir = outdir or Path(".")
    outdir.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem

    pages, doc = extract_pages_text(pdf_path)
    try:
        # -------- Layout-driven sections (unchanged) --------
        blocks_by_page = [doc[p].get_text("dict")["blocks"] for p in range(len(doc))]
        headings = detect_headings(blocks_by_page)
        sections = segment_by_headings(doc, pages, headings)

        # -------- Metadata / instruments (unchanged) --------
        fulltext = "\n\n".join(pages)
        meta = extract_metadata(doc, fulltext)
        instruments = detect_instruments(fulltext)
        aff_snip = _first_page_snippet(doc)

        # -------- NEW: Stream sentence index to JSONL.GZ --------
        # Emits one JSON object per sentence with:
        # id (e.g., S007-00123), page, text, bbox, page/global char offsets, hash16
        sent_gz_path = outdir / f"{stem}.sentences.jsonl.gz"
        global_cursor = 0

        def sentence_gen():
            nonlocal global_cursor
            for pno in range(len(pages)):
                recs, global_cursor, _ = iter_page_sentences(doc, pno, global_cursor)
                for r in recs:
                    yield {
                        "id": r.id,
                        "page": r.page,
                        "text": r.text,
                        "bbox": [r.bbox[0], r.bbox[1], r.bbox[2], r.bbox[3]],
                        "page_char_start": r.page_char_start,
                        "page_char_end": r.page_char_end,
                        "global_char_start": r.global_char_start,
                        "global_char_end": r.global_char_end,
                        "hash16": r.hash16,
                    }

        write_sentences_jsonl_gz(sent_gz_path, sentence_gen())

        # -------- Existing outputs --------
        write_pages_jsonl(outdir / f"{stem}.pages.jsonl", pages)
        write_full_text(outdir / f"{stem}.full.txt", pages)
        write_summary_json(outdir / f"{stem}.summary.json", meta, sections, instruments, aff_snip)
        write_meta_json(outdir / f"{stem}.meta.json", str(pdf_path), len(pages), meta)

    finally:
        doc.close()


def main():
    ap = argparse.ArgumentParser(
        prog="pdf-extractor",
        description="PDF text extractor with layout-driven heading detection + sentence index"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("extract", help="Extract text, pages, metadata, sections, and sentence index")
    ex.add_argument("pdf", type=Path, help="Path to PDF file")
    ex.add_argument("-o", "--outdir", type=Path, default=Path("."), help="Output directory")

    args = ap.parse_args()
    if args.cmd == "extract":
        run_extract(args.pdf, args.outdir)


if __name__ == "__main__":
    main()
