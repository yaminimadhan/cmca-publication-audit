# Quickstart Guide

Get the CMCA Publication Audit System running in 10 minutes.

## Prerequisites

- Python 3.10+
- PostgreSQL 15+ with pgvector extension
- OpenAI API key
- Terminal/command prompt

## 1. Setup (5 minutes)

### Clone and Create Environment

```bash
git clone <repository-url>
cd cmca-publication-audit-main

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Install Dependencies

```bash
# Backend
pip install -r src/backend/requirements.txt

# Frontend
pip install -r cmca_app_2/requirements.txt
```

### Configure Environment

Copy the environment template and fill in your values:

```bash
cp env.template .env
# Edit .env file with your database password and OpenAI API key
```

**For detailed configuration options:** See [INSTALLATION_GUIDE.md - Step 8](INSTALLATION_GUIDE.md#step-8-configure-environment-variables)

### Initialize Database

```bash
# Create database
createdb cmca_audit

# Run schema
psql -d cmca_audit -f Database/schema.sql

# Verify pgvector extension
psql -d cmca_audit -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Populate Embeddings

**Important:** Edit `src/store_embedding.py` lines 21-26 with your database credentials first.

```bash
cd src
python store_embedding.py
```

This loads gold standard phrases from `docs/gold_standard/goldstandard.txt` into the `sentence_embeddings` table.

**For detailed instructions:** See [INSTALLATION_GUIDE.md - Step 7](INSTALLATION_GUIDE.md#step-7-populate-gold-standard-embeddings)

## 2. Run the System (2 minutes)

### Start API Server

Open a terminal:

```bash
cd src/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify at http://localhost:8000/health - should return `{"ok": true}`

### Register a User

Open another terminal:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123", "user_type": "admin"}'
```

Save the returned `access_token` for API calls, or proceed to Web UI.

### Start Web UI

Open another terminal:

```bash
cd cmca_app_2
streamlit run app.py
```

Browser opens at http://localhost:8501

## 3. Upload and Process a PDF (2 minutes)

### Via Web UI

1. **Login:** Enter username `admin` and password `admin123` (or your registered credentials)
2. **Create Project:**
   - Expand "Create New Project"
   - Enter project name: "Test Project"
   - Click "Create Project"
3. **Upload PDF:**
   - Expand "Upload New PDF"
   - Select a scientific PDF from your computer (must contain text, not scanned images)
   - Choose "Test Project" from dropdown
   - Click "Upload"
4. **Wait for Processing:** Upload typically takes 10-30 seconds depending on PDF length and OpenAI API response time
5. **View Results:**
   - Dashboard shows the uploaded PDF card
   - Look for CMCA Yes/No badge
   - Pie chart updates with acknowledgement status
   - Bar chart shows detected instruments

### Via API

Alternatively, upload via curl:

```bash
TOKEN="your-access-token-from-registration"

curl -X POST http://localhost:8000/pdfs/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/sample.pdf" \
  -F "project_id=1"
```

Response includes:
```json
{
  "pdf_id": 1,
  "title": "Sample Paper Title",
  "authors": "Author One; Author Two",
  "doi": "10.1234/example.2024",
  "instruments_json": ["SEM", "TEM", "XRD"],
  "num_pages": 12,
  "cmca_result": "Yes",
  "cosine_similarity": 0.8456,
  "storage_path": "storage/pdfs/abc123.pdf",
  "upload_date": "2025-10-14T12:34:56.789Z"
}
```

## 4. Inspect Results (1 minute)

### Dashboard View

- **Charts:** Top of page shows:
  - Pie chart: CMCA Yes vs No distribution
  - Bar chart: Top 5 instruments by PDF count
- **Filters:** Filter by project, instrument type; sort by date or title
- **PDF Cards:** Each card shows:
  - Title and CMCA result badge (Yes / No)
  - Project, instruments, upload date
  - "Open" button to view details

### Detail View

Click "Open" on a PDF card:

- **Metadata:** Title, authors, DOI, instruments, page count, publish date
- **Scores:** Cosine similarity score (0-1), CMCA result (Yes/No)
- **Download:** "Download PDF" button retrieves the PDF with yellow highlights on verified acknowledgement sentences
- **Edit:** Update metadata fields if extraction was incorrect
- **Delete:** Remove PDF from system

### Highlighted PDF

The downloaded PDF contains yellow highlight annotations on sentences classified as "Answer: Yes" by GPT-4o. These are the sentences that formally acknowledge CMCA, UWA, Microscopy Australia, or NCRIS support.

**Implementation:** `src/backend/app/services/highlight_service.py:8-59`

## Cleanup

Stop the servers with Ctrl+C in each terminal, then:

```bash
deactivate  # Exit virtual environment
```

To reset the database:

```bash
dropdb cmca_audit
createdb cmca_audit
psql -d cmca_audit -f Database/schema.sql
```

## FAQ

### Where are embeddings stored?

Embeddings are stored in the PostgreSQL `sentence_embeddings` table (`Database/schema.sql:43-47`):

```sql
CREATE TABLE sentence_embeddings (
    id SERIAL PRIMARY KEY,
    sentence TEXT NOT NULL,
    embedding VECTOR(768)
);
```

The table contains gold standard acknowledgement phrases from `docs/gold_standard/goldstandard.txt`, each with a 768-dimensional vector from the intfloat/e5-base-v2 model.

### What PDF metadata is extracted?

The extraction service (`src/backend/app/services/extraction_service.py:402-514`) parses:

1. **Title:** Largest font spans near top of first page (line 164-222)
2. **Authors:** Font size below title, cleaned of affiliation markers (line 224-265)
3. **DOI:** Regex pattern `10.xxxx/...` (line 106, 459)
4. **Instruments:** Keyword matching (SEM, TEM, AFM, XRD, etc.) (line 270-287)
5. **Page Count:** Number of pages in PDF (line 506)
6. **Sentences:** Text split into sentences with stable IDs like `p1_s5` (line 297-325, 434-453)

Additional fields like `publish_date` and `affiliation` are placeholders (returned as None) for future enhancement.

### How are acknowledgements verified?

Two-stage pipeline (`src/backend/app/services/llm_service.py:46-127`):

1. **Similarity Search:** Each sentence is embedded with intfloat/e5-base-v2 and compared to gold standard phrases using cosine similarity via pgvector (`src/backend/app/services/similarity_search.py:9-38`). Top k=30 matches are retrieved.

2. **Threshold Filter:** Only sentences with similarity >= 0.70 are passed to LLM (line 61-65).

3. **LLM Classification:** GPT-4o (temperature 0.0) receives a structured prompt (line 11-43) with the sentence and its top similarity match. The LLM outputs "Answer: Yes" or "Answer: No" with a 1-3 line reason. If GPT-4o quota is exceeded, the system falls back to gpt-3.5-turbo (line 93-103).

4. **Result:** If any sentence is classified "Yes", the PDF's `cmca_result` is "Yes"; otherwise "No". The highest cosine similarity score is stored in `cosine_similarity` field.

### What if the extraction is wrong?

Use the Web UI detail page or API `PATCH /pdfs/{pdf_id}` to manually correct:
- Title
- Authors
- DOI
- Affiliation
- Instruments
- Publish date
- CMCA result

See `src/backend/app/routers/pdfs.py:114-145` for the update endpoint.

### Can I process multiple PDFs at once?

**API:** Yes, loop over files and POST to `/pdfs/upload` with your JWT token

**Web UI:** Currently single-file upload. TODO: Add batch upload feature.

**Batch Processing Example:**
```bash
# Process multiple PDFs via API
for pdf in *.pdf; do
  curl -X POST http://localhost:8000/pdfs/upload \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -F "file=@$pdf" \
    -F "project_id=1"
done
```

### How do I export results to CSV/XLSX?

Manual export via SQL:

```bash
psql -d cmca_audit -c "COPY (SELECT pdf_id, title, authors, doi, cmca_result, cosine_similarity, upload_date FROM pdfs) TO '/tmp/export.csv' WITH CSV HEADER;"
```

### What models are used?

- **Embeddings:** intfloat/e5-base-v2 (768-dim, sentence-transformers)
- **LLM:** OpenAI GPT-4o (primary), GPT-3.5-turbo (fallback on quota)
- **NER (optional):** spaCy en_core_web_trf (used in `src/match.py` for staff/instrument mention detection)

### Where are PDF files stored?

Physical files are saved to the directory specified by `UPLOAD_DIR` environment variable (default: `storage/pdfs/`). Filename is UUID + `.pdf` extension. The database `pdfs.storage_path` column stores the full path.

**Implementation:** `src/backend/app/services/pdf_service.py:79-85`

### How long does processing take per PDF?

Typical timeline:
- Extraction: 1-3 seconds (PyMuPDF parsing)
- Embedding: 2-5 seconds (sentence-transformers encoding)
- Similarity search: <1 second (pgvector query)
- LLM verification: 5-15 seconds per sentence (OpenAI API calls), up to 7 top sentences
- Highlighting: <1 second
- **Total: 10-30 seconds per PDF**

Bottleneck is OpenAI API latency. For large batches, consider parallelization or caching.

### Troubleshooting: "No 'Answer: Yes' sentences found"

This message (`highlight_service.py:30`) means the LLM did not classify any sentence as a formal acknowledgement of CMCA/UWA/Microscopy Australia. Possible causes:

1. **No acknowledgements section:** Paper lacks an acknowledgements section
2. **Generic thanks:** Acknowledgements only thank individuals, not institutions/facilities
3. **Similarity threshold too high:** Lower threshold in `llm_service.py:46` from 0.70 to 0.60
4. **Gold standard mismatch:** Phrases in `goldstandard.txt` don't cover paper's wording; add new phrases and re-run `store_embedding.py`

### Troubleshooting: "Highlighting failed"

Error in `pdf_service.py:75`. Common causes:

1. **Text not found:** PyMuPDF's `page.search_for(sentence_text)` returns empty if sentence spans multiple lines or uses different whitespace/hyphenation. The system logs a warning but continues with unhighlighted PDF.
2. **Malformed PDF:** Some PDFs have corrupted structure. The system falls back to saving the original PDF.

Check logs for specific warnings like `[warn] Text not found on page X`.

---

**Next Steps:**

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Read [REPORT_SECTIONS.md](REPORT_SECTIONS.md) for methods and evaluation
- Explore API docs at http://localhost:8000/docs
- Review `Database/schema.sql` for full database schema

**Support:** For issues, check [README.md](README.md) Troubleshooting section.

