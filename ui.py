# CMCA Publication Audit — Stage-2 UI (Pilot)
# Upload a PDF → run extractor → show/download equipment table (JSON/XLSX).
# - If stage-1 extractor is importable (src/extraction/extract_pdf_text.py), we call it.
# - Otherwise we use a built-in heuristic fallback to build an equipment table.

from __future__ import annotations
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd

# Optional deps for PDF parsing; we try PyMuPDF (fitz) then pdfplumber
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    import pdfplumber
except Exception:
    pdfplumber = None

# ----- Try loading the Stage-1 extractor -----
ROOT = Path(__file__).resolve().parents[1]  # repo root (assumes ui/ is one level below)
sys.path.insert(0, str(ROOT / "src"))
HAS_EXTRACTOR = False
try:
    from extraction.extract_pdf_text import run_extract as stage1_run_extract  # type: ignore
    HAS_EXTRACTOR = True
except Exception:
    HAS_EXTRACTOR = False

# ----- Heuristic fallback (vendor/model patterns) -----
import re
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
VENDORS = [
    "Shimadzu","Agilent","Thermo Fisher","Thermo","Bruker","Nikon","Zeiss","JEOL","FEI",
    "Asylum Research","Ossila","Roche","Illumina","Rigaku","Xenocs","Micromeritics","Magritek","Gatan","Oxford Instruments"
]
MODEL_PAT = re.compile(r"\b([A-Z]{1,4}\s?-?\d{1,4}[A-Za-z0-9\-]*|MFP-3D|Dimension Icon|Icon|Verios\s?XHR|SmartLab|HyPix-3000|Pilatus\s?\d+|LightCycler\s?480\s?II)\b")
EQUIP_HINTS = [
    "sem","tem","afm","xrd","nmr","ftir","raman","spectrophot","microscope","spectrometer","chromatograph",
    "zeiss","jeol","fei","rigaku","xenocs","thermo","bruker","illumina","ossila","micromeritics","magritek"
]
ACK_HINTS = [
    "Centre for Microscopy", "CMCA", "Microscopy Australia", "NCRIS",
    "Centre for Microscopy, Characterisation and Analysis",
    "Centre for Microscopy, Characterization and Analysis",
    "The University of Western Australia", "UWA"
]
DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)

def sentence_split(text: str) -> List[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text or "") if s.strip()]

def guess_vendor(text: str) -> Optional[str]:
    t = text.lower()
    for v in VENDORS:
        if v.lower() in t:
            return "Thermo Fisher" if v.lower().startswith("thermo") else v
    return None

def read_pdf_pages(path: Path) -> List[str]:
    pages: List[str] = []
    if fitz is not None:
        try:
            doc = fitz.open(str(path))
            for i in range(len(doc)):
                pages.append((doc.load_page(i).get_text("text") or "").strip())
        except Exception:
            pass
    if not pages and pdfplumber is not None:
        try:
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text() or ""
                    pages.append(txt.strip())
        except Exception:
            pass
    return pages

def fallback_extract(path: Path, outdir: Path) -> Dict:
    outdir.mkdir(parents=True, exist_ok=True)
    pages = read_pdf_pages(path)
    fulltext = "\n\n".join(pages)
    # Save basic artifacts
    (outdir / "fulltext.txt").write_text(fulltext, encoding="utf-8")
    with (outdir / "pages.jsonl").open("w", encoding="utf-8") as f:
        for i, t in enumerate(pages, start=1):
            f.write(json.dumps({"page": i, "text": t}, ensure_ascii=False) + "\n")
    doi_match = DOI_RE.search("\n".join(pages[:2]) if pages else "") or DOI_RE.search(fulltext)
    metadata = {"doi": doi_match.group(0) if doi_match else None}
    (outdir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Build equipment table from sentences
    rows: List[Dict] = []
    for pno, text in enumerate(pages, start=1):
        for sent in sentence_split(text):
            if any(tok in sent.lower() for tok in EQUIP_HINTS):
                manu = guess_vendor(sent)
                m = MODEL_PAT.search(sent)
                model = m.group(1) if m else None
                name = (f"{manu} {model}".strip() if manu and model else manu) if (manu or model) else None
                rows.append({
                    "equipment_name": name,
                    "manufacturer": manu,
                    "model": model,
                    "specs": {},
                    "section": None,
                    "page": pno,
                    "context": sent[:400]
                })
    # Deduplicate
    seen = set(); ded = []
    for r in rows:
        key = (r["page"], (r.get("context") or "")[:120].lower())
        if key in seen: 
            continue
        seen.add(key); ded.append(r)
    table = ded
    # Save outputs
    (outdir / "equipment_table.json").write_text(json.dumps({"table": table}, indent=2), encoding="utf-8")
    pd.DataFrame(table).to_excel(outdir / "equipment_table.xlsx", index=False)
    return {"table": table, "metadata": metadata}

# ----- UI -----
st.set_page_config(page_title="CMCA Publication Audit — Stage-2 UI", layout="wide")
st.title("CMCA Publication Audit — Stage-2 UI (Pilot)")
st.caption("Upload a PDF → extract equipment table (JSON/XLSX). Uses Stage-1 extractor if present; otherwise a built-in fallback.")

col1, col2 = st.columns([2, 1])
with col2:
    st.write("**Extractor backend**")
    st.success("Using Stage-1 module found in src/extraction" if HAS_EXTRACTOR else "Fallback extractor (UI-built)")

with col1:
    uploaded = st.file_uploader("Upload a scientific PDF", type=["pdf"])

run_btn = st.button("Run Extraction", use_container_width=True, type="primary", disabled=uploaded is None)

if run_btn and uploaded:
    # Prepare output dir and write the uploaded file
    stamp = time.strftime("%Y%m%d-%H%M%S")
    outdir = ROOT / "ui" / "outputs" / f"run_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)
    pdf_path = outdir / "input.pdf"
    pdf_path.write_bytes(uploaded.getbuffer())

    with st.status("Extracting…", expanded=True) as status:
        st.write("Saving PDF…")
        st.write(f"Output folder: `{outdir}`")
        if HAS_EXTRACTOR:
            st.write("Calling Stage-1 extractor…")
            try:
                stage1_run_extract(pdf_path, outdir)
                st.write("Stage-1 extractor finished.")
            except Exception as e:
                st.error(f"Stage-1 extractor failed: {e}")
                st.write("Falling back to built-in extractor…")
                fallback_extract(pdf_path, outdir)
        else:
            st.write("Using built-in fallback extractor…")
            fallback_extract(pdf_path, outdir)
        status.update(label="Done.", state="complete")

    # Load and show the equipment table
    table_json = outdir / "equipment_table.json"
    if table_json.exists():
        data = json.loads(table_json.read_text(encoding="utf-8"))
        rows = data.get("table", [])
        df = pd.DataFrame(rows)
        st.subheader("Equipment Table")
        if df.empty:
            st.info("No equipment-like sentences found.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Download buttons
        st.subheader("Download")
        # JSON
        st.download_button(
            "Download equipment_table.json",
            data=json.dumps({"table": rows}, indent=2),
            file_name="equipment_table.json",
            mime="application/json"
        )
        # XLSX
        xls_buf = io.BytesIO()
        pd.DataFrame(rows).to_excel(xls_buf, index=False)
        st.download_button(
            "Download equipment_table.xlsx",
            data=xls_buf.getvalue(),
            file_name="equipment_table.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.error("equipment_table.json not found — something went wrong. Check logs in the output folder.")
