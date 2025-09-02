import argparse, json, re, sys
from pathlib import Path
import pandas as pd

# Defaults (can be overridden by CLI flags)
IN_XLSX = Path("data/Gold_Standard_v2.xlsx")  
SHEET   = "Gold_Standard_Template"             
OUTDIR  = Path("json_out"); OUTDIR.mkdir(exist_ok=True)

# Exact headers (line breaks included)
C = {
    "case_id": "Case\nID",
    "authors": 'Authors (Family name, Initial. \n"and" before the final author)',
    "title": "Title",
    "journal": "Journal",
    "doi": "DOI",

    # Acknowledgement
    "ack_present": "CMCA_Acknowledged\n (Yes/No),\n\nincluding NIF, MicroAust Metabolomics etc",
    "ack_text": "CMCA_Ack_Exact_Text",
    "ack_pages_sections": None,  # set to real header later if added

    # Affiliation
    "aff_present": "CMCA_Affiliation_in_Text \n(Yes/No)",
    "aff_snips":  "Acknowledgement/Affiliation \n(Snippets)",

    # Coauthors
    "co_present": "CMCA Co-author\n (Yes/No)",
    "co_names":   "CMCA Co-author \nName(s)",

    # Instruments
    "instr_verbatim": "Instrument_Terms (verbatim)",

    # Labels
    "label_initial":     "Label \n\n(Positive/\nNegative/\nAmbiguous)",
    "label_adjudicated": "Adjudicated_Label",
    "negative_type":     "Negative_Type \n(Random/Hard)",
    "rationale":         "Notes",
}

# -------------------------
# Helper functions
# -------------------------

def yn(cell):
    if cell is None: return None
    s = str(cell).strip().lower()
    if s in {"y","yes","true","1"}: return True
    if s in {"n","no","false","0"}: return False
    return None

def parse_ack_pages_sections(cell):
    """Parse 'p.8,11 (Methods section)' -> {'pages':[8,11],'sections':['Methods']}"""
    if not cell or str(cell).strip()=="":
        return {"pages": [], "sections": []}
    s = str(cell)
    m = re.search(r"\(([^)]+)\)", s)
    section = m.group(1) if m else None
    if section:
        section = re.sub(r"\s*section\b", "", section, flags=re.I).strip()
    pages_part = re.sub(r"\(.*?\)", "", s)
    pages_part = re.sub(r"pp?\.?", "", pages_part, flags=re.I)
    toks = re.split(r"[,\s/]+", pages_part)
    pages = [int(t) for t in toks if t.isdigit()]
    return {"pages": pages, "sections": ([section] if section else [])}

def split_multiline(val):
    if not val or str(val).strip()=="":
        return []
    s = str(val)
    # Support "AND" and quoted bullet formats
    s = re.sub(r"\s+\bAND\b\s+", "\n", s, flags=re.I)
    s = re.sub(r"^\s*>\s*", "", s, flags=re.M)
    parts = re.split(r"[\n\r;]+", s)
    return [p.strip(" -\t") for p in parts if p.strip()]

def split_names(val):
    if not val or str(val).strip()=="":
        return []
    return [x.strip() for x in re.split(r"[;,]", str(val)) if x.strip()]

def prune(x):
    if isinstance(x, dict):
        return {k: prune(v) for k, v in x.items() if v not in [None, "", [], {}]}
    if isinstance(x, list):
        return [prune(v) for v in x if v not in [None, "", [], {}]]
    return x

def check_headers(df):
    missing = []
    for k, header in C.items():
        if header is None: 
            continue
        if header not in df.columns:
            missing.append((k, header))
    if missing:
        print("\n[ERROR] These headers weren't found in the sheet:")
        for k, h in missing:
            print(f"  - {k}: expected column header -> {repr(h)}")
        print("\nAvailable columns are:\n  " + "\n  ".join(map(repr, df.columns.tolist())))
        sys.exit(2)

# -------------------------
# Main logic
# -------------------------

def main(xlsx, sheet, limit=None):
    df = pd.read_excel(xlsx, sheet_name=sheet, dtype=str).fillna("")
    check_headers(df)
    all_objs = []

    for i, r in df.iterrows():
        if limit is not None and i >= limit:
            break

        case_id = str(r.get(C["case_id"], "")).strip() or str(i+1)
        ack_loc = {"pages": [], "sections": []}
        if C["ack_pages_sections"]:
            ack_loc = parse_ack_pages_sections(r.get(C["ack_pages_sections"], ""))

        obj = {
            "case_id": case_id,
            "metadata": {
                "title":   r.get(C["title"], "") or None,
                "doi":     r.get(C["doi"], "") or None,
                "journal": r.get(C["journal"], "") or None
            },
            "authors_verbatim": r.get(C["authors"], "") or None,

            "acknowledgement": {
                "present":   yn(r.get(C["ack_present"], "")),
                **({"pages": ack_loc["pages"]} if ack_loc["pages"] else {}),
                **({"sections": ack_loc["sections"]} if ack_loc["sections"] else {}),
                **({"exact_text": r.get(C["ack_text"], "")} if r.get(C["ack_text"], "") else {})
            },

            "cmca_affiliation": {
                "present": yn(r.get(C["aff_present"], "")),
                "snippets": split_multiline(r.get(C["aff_snips"], "")),
            },

            "cmca_coauthors": split_names(r.get(C["co_names"], "")),

            "instruments": [{"verbatim": s} for s in split_multiline(r.get(C["instr_verbatim"], ""))],

            "labels": {
                "initial":       r.get(C["label_initial"], "") or None,
                "adjudicated":   r.get(C["label_adjudicated"], "") or None,
                "negative_type": r.get(C["negative_type"], "") or None,
                "rationale":     r.get(C["rationale"], "") or None
            },

            "provenance": {
                "source": {"type": "doi", "id": (r.get(C["doi"], "") or None)}
            }
        }

        obj = prune(obj)
        (OUTDIR / f"{case_id}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        all_objs.append(obj)

    (OUTDIR / "gold_standard_all.json").write_text(json.dumps(all_objs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(all_objs)} case(s) → {OUTDIR.resolve()}")

# -------------------------
# Entry point
# -------------------------

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--xlsx", default=str(IN_XLSX), help="Path to Excel file")
    p.add_argument("--sheet", default=SHEET, help="Worksheet name")
    p.add_argument("--limit", type=int, default=None, help="Export only first N rows")
    args = p.parse_args()
    main(args.xlsx, args.sheet, limit=args.limit)
