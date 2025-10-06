from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import json
import gzip, json
from typing import Iterable

def write_pages_jsonl(path: Path, pages: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for i, txt in enumerate(pages, start=1):
            rec = {"page": i, "text": txt}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def write_full_text(path: Path, pages: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("\n\n".join(pages))

def write_summary_json(path: Path, metadata: Dict, sections: List[Dict], instruments: List[str], affiliations_snippet: str|None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "metadata": metadata,
        "sections": { s["title"]: s["content"] for s in sections },
        "instruments_found": instruments,
        "affiliations_first_page_snippet": affiliations_snippet or ""
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

def write_meta_json(path: Path, pdf_file: str, num_pages: int, metadata: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"file": pdf_file, "num_pages": num_pages, **metadata}
    with path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def write_sentences_jsonl_gz(path: Path, sentences: Iterable[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for rec in sentences:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")