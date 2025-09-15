# CMCA LLM Publication Audit

This project automates the annual CMCA publication audit using Large Language Models (LLMs).

## Stages
- Stage 1: CLI + API (FastAPI)
- Stage 2: Web GUI (React/Streamlit)

# Stage-2 UI (Pilot)

A simple Streamlit UI to upload a PDF and extract an equipment table (JSON/XLSX).

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r ui/requirements.txt

streamlit run ui/app.py
