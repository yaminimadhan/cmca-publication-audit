# Gold Standard JSON Dataset

This repository contains the **gold standard dataset** for the CMCA publication audit project.  
The dataset is curated directly from PDFs and exported to JSON for evaluation and pipeline comparison.

## Contents
- `scripts/export_json.py` – Python script to generate JSON from the gold standard Excel.  
- `json_out/` – exported JSONs:
  - `1.json … 30.json` – one JSON per case.  
  - `gold_standard_all.json` – all cases in one array.  

## Schema Notes
- JSON includes **only PDF-verified fields**:
  - Acknowledgement (present, text, pages/sections if tracked)  
  - CMCA affiliation (present, snippets)  
  - CMCA coauthors  
  - Instruments (verbatim list from PDF)  
  - Labels (initial, adjudicated, negative type, rationale)  
  - Provenance (DOI as source)
- **Audit-only fields are excluded**:
  - `CMCA platform used`  
  - `Platform simplified term`  
  - `Instrument code`  

These remain in the Excel for reference but are **not part of the JSON ground truth**.

## How to Regenerate
The JSONs in `json_out/` are already generated.  
To regenerate from the Excel:

```bash
pip install pandas openpyxl
python scripts/export_json.py --xlsx data/Gold_Standard_v2.xlsx --sheet "Gold_Standard_Template"
