---
editor_options: 
  markdown: 
    wrap: 72
---

# CMCA Publication Audit System: A Semi-Automated Pipeline for Microscopy Facility Acknowledgement Detection

## Abstract

The Centre for Microscopy Characterisation and Analysis (CMCA) requires
annual audits of scientific publications acknowledging their facilities.
This project implements a semi-automated system that ingests PDF
publications, extracts metadata and acknowledgements using PyMuPDF
[@pymupdf], scores relevance via sentence embedding similarity
(intfloat/e5-base-v2 [@wang2022e5] with pgvector [@pgvector]) and LLM
verification (GPT-4o [@openai2023gpt4]), and provides a multi-user web
interface for review and management. The system achieves end-to-end
automation from upload to annotated PDF output with highlighted
acknowledgement sentences. Implemented components include FastAPI REST
API [@fastapi] with JWT authentication [@rfc7519], PostgreSQL database
[@postgresql] with vector similarity search, Streamlit web UI
[@streamlit] with project management and visualization, and a hybrid
heuristic-LLM pipeline balancing throughput, cost, and accuracy.

## 1. Introduction

### Challenge and Significance

CMCA and Microscopy Australia [@microscopy_australia] facilities support
numerous research projects annually through microscopy instrumentation
and technical expertise. Tracking publications that acknowledge these
facilities is critical for demonstrating research impact to funding
bodies (NCRIS [@ncris2023]), justifying infrastructure investment, and
maintaining institutional accountability. Manual auditing of hundreds of
publications is time-intensive and error-prone, requiring reading entire
PDFs to locate acknowledgement sections and determine relevance.

### Project Objectives

This system automates the publication audit workflow by:

1.  **Ingesting** scientific publication PDFs from researchers and
    administrators
2.  **Extracting** structured metadata (title, authors, DOI,
    instruments) and sentence-level text with layout awareness
3.  **Scoring** acknowledgement relevance to CMCA/Microscopy
    Australia/UWA/NCRIS using embedding similarity and LLM
    classification
4.  **Annotating** verified acknowledgement sentences with yellow
    highlights for human review
5.  **Storing** results in a structured database supporting multi-user,
    multi-project workflows
6.  **Reviewing** PDFs via web interface with filtering, charts, and
    export capabilities

**Data Description:**

-   **Input:** Scientific publication PDFs (text-based, not scanned
    images)
-   **Gold Standard:** 44 curated acknowledgement phrases
    (`docs/gold_standard/goldstandard.txt`) covering CMCA, UWA,
    Microscopy Australia, and NCRIS mentions (Database/schema.sql:43-47)
-   **Output:** PDF metadata, acknowledgement classification (Yes/No),
    cosine similarity scores, highlighted PDFs with yellow annotations

### Team Approach and Stage Completion

The project follows four implementation stages defined in the original
scope (Project_outline_draft.docx):

| Stage | Description | Status | Evidence |
|----------------|-----------------------|----------------|-----------------|
| **1** | FastAPI backend API | Complete | src/backend/app/main.py, routers in src/backend/app/routers/ |
| **2A** | Basic web GUI (Streamlit) | Complete | cmca_app_2/app.py with TinyDB fallback storage |
| **2B** | Advanced web GUI features | Complete | User auth, projects, charts, filtering in cmca_app_2/pages/ |

**Implemented:** Multi-user REST API, PostgreSQL with pgvector, PDF
extraction with PyMuPDF, sentence embedding similarity,
GPT-4o/GPT-3.5-turbo LLM verification, PDF highlighting, Streamlit web
UI with authentication and visualization.

## 2. Methods (as shown in Github) & Results

### 2.1 PDF Text Extraction and Metadata Parsing

**Purpose:** Parse text, metadata, and sentences from research PDFs with
diverse layouts (single/double column, varied fonts) to enable
downstream acknowledgement detection.

**Method:** PyMuPDF (fitz) [@pymupdf] layout-aware extraction
(src/backend/app/services/extraction_service.py:402-514).

**Key Steps:**

1.  **Layout Detection:** Extract text blocks with bounding boxes via
    `page.get_text("blocks")` (line 52); sort by Y-coordinate
    (top-to-bottom), then X-coordinate (left-to-right) (line 57-58)
2.  **Column Detection:** Analyze left-edge X positions; if gap between
    clusters \>40px, infer two-column layout (line 60-76); split blocks
    at midpoint and merge in reading order: left column top-down, then
    right column top-down (line 92-101)
3.  **Sentence Segmentation:** Split text on regex
    `[.?!] + space + [A-Z(]` with guards for abbreviations (e.g., "et
    al.", "i.e.") (line 297-325); assign stable IDs like `p2_s12` (page
    2, sentence 12) (line 449)
4.  **Title Extraction:** Identify largest font spans in top 40% of page
    1 via `page.get_text("dict")` (line 164-222); sort by Y,X to join
    multi-line titles
5.  **Author Extraction:** Font size below title, \<title size, ≥10pt
    (avoids footnotes); strip affiliation markers (`*`, digits, `†`,
    `‡`, `§`, `#`); split on commas/"and"; keep 2-5 word tokens (line
    224-265)
6.  **DOI:** Regex `10.\d{4,9}/[-._;()/:A-Z0-9]+` in first two pages
    (line 106, 459-460)
7.  **Instruments:** Keyword matching (SEM, TEM, AFM, XRD, NMR, FTIR,
    Zeiss, Bruker, JEOL, etc.) (line 270-287)

**Key Parameters:** - Two-column threshold: 40px gap (line 73 in
extraction_service.py) - Author font size: 10-18pt range (line 229) -
Author band: 250px below title (line 227)

**Data Flow:** API route `POST /pdfs/upload`
(src/backend/app/routers/pdfs.py:31-58) receives file bytes → passes to
`PdfService.ingest()` (src/backend/app/services/pdf_service.py:40-102) →
calls `extract_api(file_bytes)` → returns JSON with keys: `title`,
`authors`, `doi`, `instruments` (list), `num_pages`, `sentences` (list
of dicts with `id`, `page`, `index`, `text`).

**Outputs:** Extracted metadata stored in `pdfs` table
(Database/schema.sql:20-42); sentence array passed to LLM verification.

**Results:**  **TBD** - Extraction accuracy not yet measured.
**TODO:** Create tests/test_extraction.py with sample PDFs from diverse
publishers (Nature, Elsevier, IEEE, PLOS) and ground truth annotations;
measure exact match accuracy and fuzzy match F1 for
title/authors/DOI/instruments.

**Observed Limitations:** - Scanned PDFs (no text layer) return empty
results (no OCR support) - 3+ column or irregular layouts may produce
misordered text - Title extraction fails if title uses non-largest font
or spans blocks with different fonts

### 2.2 Embedding Similarity Search

**Purpose:** Retrieve top-k gold standard phrases semantically matching
each PDF sentence, filtering candidates for LLM verification to reduce
API costs.

**Method:** Sentence-transformers [@reimers2019sentence]
(intfloat/e5-base-v2 [@wang2022e5]) + pgvector [@pgvector] cosine
similarity [@salton1975vector]
(src/backend/app/services/similarity_search.py:9-38).

**Key Steps:**

1.  **Embedding Model:** intfloat/e5-base-v2 [@wang2022e5] (BERT-based
    [@devlin2019bert], 768-dimensional vectors) via
    sentence-transformers [@reimers2019sentence] (line 6)

2.  **Gold Standard Population:** Load phrases from
    docs/gold_standard/goldstandard.txt → encode with prefix "Query: "
    (e5 requirement) → insert into PostgreSQL `sentence_embeddings`
    table as `VECTOR(768)` type (src/store_embedding.py:14-44)

3.  **Query:** Encode PDF sentences in batch → for each, execute SQL:

    ``` sql
    SELECT sentence, 1 - (embedding <=> %s::vector) AS cosine_similarity
    FROM sentence_embeddings
    ORDER BY embedding <=> %s::vector
    LIMIT k;
    ```

    where `<=>` is pgvector L2 distance; `1 - distance` approximates
    cosine similarity [@salton1975vector] for unit-normalized vectors
    (line 28-33)

4.  **Return:** Dict mapping
    `{query_sentence: [(matched_phrase, similarity_score), ...]}`

**Key Parameters:** - k=30 (line 9 in similarity_search.py) - retrieve
top 30 matches per sentence - Threshold=0.70 (in llm_service.py:46) -
only sentences with ≥1 match above threshold proceed to LLM

**Data Flow:** LLM service calls
`search_sentences(sentences_text, k=30)` → returns similarity dict →
filters by threshold ≥0.70 → ranks by best score → takes top 7 for LLM
verification (src/backend/app/services/llm_service.py:58-75).

**Outputs:** Filtered candidate sentences with provenance (top matched
phrase + score).

**Results:**  **TBD** - Similarity search performance not benchmarked.
**TODO:** Create src/benchmark_similarity.py with 50-100 labeled
sentences (positive/negative acknowledgements); compute
[precision\@k](mailto:precision@k){.email} (k=1,5,10,30), recall, and
precision-recall curve for thresholds 0.5-0.9; analyze false negatives
(paraphrased acknowledgements below threshold).

**Trade-off:** Higher k increases recall but adds LLM API calls;
threshold 0.70 balances precision/recall to reduce false positives.

### 2.3 LLM Acknowledgement Verification

**Purpose:** Classify if a sentence constitutes a formal acknowledgement
of CMCA/UWA/Microscopy Australia/NCRIS, providing explainable Yes/No
decisions.

**Method:** OpenAI GPT-4o [@openai2023gpt4; @openai_gpt4o] with
structured prompt (src/backend/app/services/llm_service.py:46-127).

**Key Steps:**

1.  **Candidate Selection:** Filter sentences with similarity ≥0.70
    (line 61-65) → rank by best similarity score → take top 7 (line 75,
    `top_k=7` parameter at line 46)
2.  **Prompt Construction:** (line 11-43, function `build_prompt`)
    -   System role: "You are acting as a research compliance auditor"
        (line 88)
    -   User prompt includes: extracted sentence, top similarity match +
        score (provenance), task definition, target entities
        (CMCA/UWA/Microscopy Australia/NCRIS), decision criteria (must
        refer to facility use, technical assistance, or funding; not
        generic thanks), output format: "Answer: [Yes or No]\nReason:
        (1-3 lines)"
3.  **LLM Inference:**
    -   Model: GPT-4o [@openai2023gpt4] (`gpt-4o`, line 86), temperature
        0.0 (deterministic, line 91)
    -   Fallback: On `openai.RateLimitError`, retry with `gpt-3.5-turbo`
        [@brown2020language] (line 93-103)
4.  **Response Parsing:** Check if response contains "Answer: Yes" (line
    108); extract full response text for logging (line 105)
5.  **Aggregation:** If any sentence is "Yes", set `cmca_result = "Yes"`
    (line 124); record max cosine similarity across all candidates (line
    125)

**Key Parameters:** - top_k=7 (line 46) - limit LLM calls to control
cost and latency - threshold=0.70 (line 46) - pre-filter low-similarity
sentences - temperature=0.0 (line 91) - deterministic output for
reproducibility

**Data Flow:** `run_llm_verification_from_json(extractor_json)` receives
sentences → embeds and searches → filters and ranks → for each top
candidate: builds prompt → calls OpenAI API → parses response →
aggregates to final `cmca_result` and `cosine_similarity`.

**Outputs:** Returns payload:

``` python
{
  "cmca_result": "Yes" | "No",
  "cosine_similarity": float (0-1),
  "Sentence_verifications": [
    {"sentence_id": str, "page": int, "index": int,
     "query_text": str, "similarity_score": float,
     "llm_response": str},
    ...
  ]
}
```

**Results:**  **TBD** - LLM classification accuracy not evaluated.
**TODO:** Create src/eval_llm.py to manually label 100-200 sentences as
TP/TN/FP/FN; run LLM verification; compute confusion matrix, precision,
recall, F1; analyze errors (false positives: generic thanks; false
negatives: non-standard phrasing); compare GPT-4o vs GPT-3.5-turbo
performance.

**Cost Analysis:** GPT-4o: \~\$0.005 per sentence (\~200 input tokens,
\~50 output tokens); GPT-3.5-turbo fallback: \~\$0.0005 per sentence;
typical PDF: 7 sentences → \$0.035 per PDF (GPT-4o) or \$0.0035
(GPT-3.5-turbo).

**Evidence of Fallback:** Line 93-103 catches `openai.RateLimitError`
and retries with `gpt-3.5-turbo`, logging "Quota exceeded: falling back
to gpt-3.5-turbo..."

### 2.4 PDF Highlighting and Annotation

**Purpose:** Annotate verified acknowledgement sentences with yellow
highlights in PDF for human reviewers to quickly verify LLM decisions.

**Method:** PyMuPDF [@pymupdf] annotation
(src/backend/app/services/highlight_service.py:8-59).

**Key Steps:**

1.  **Filter "Answer: Yes" Sentences:** Parse `llm_outputs` list →
    extract `sentence_id` for entries where
    `llm_response.startswith("Answer: Yes")` (line 23-28)
2.  **Lookup Sentence Metadata:** Map sentence IDs to sentence text and
    page number from `sentences` list (line 21, 37-40)
3.  **Annotate PDF:** Open PDF from memory via
    `fitz.open(stream=pdf_bytes, filetype="pdf")` (line 34) → for each
    "Yes" sentence: navigate to page (line 45) → search for sentence
    text via `page.search_for(sentence_text)` returning list of bounding
    rectangles (line 46) → add yellow highlight annotation:
    `page.add_highlight_annot(rect)` with RGB (1, 1, 0) (line 52-54)
4.  **Export:** Save annotated PDF to bytes buffer with garbage
    collection and deflate compression (line 57-59)

**Key Parameters:** - Highlight color: Yellow RGB (1, 1, 0) (line 12) -
Compression: `garbage=4, deflate=True` (line 58)

**Data Flow:** `pdf_service.py:68-76` calls
`highlight_answer_yes_sentences_from_bytes(pdf_bytes, sentences, llm_outputs)`
→ returns highlighted PDF bytes → writes to file storage.

**Outputs:** Highlighted PDF stored at `UPLOAD_DIR/{uuid}.pdf` with
`storage_path` column in database.

**Limitations:** If `page.search_for()` returns empty (line 47-49),
sentence not highlighted due to multi-line splits or different
whitespace/hyphenation; logs warning but continues. Fallback:
pdf_service.py:68-76 wraps in try/except; on error, returns original
(unhighlighted) PDF.

### 2.5 Database Schema and Storage

**Purpose:** Store users, projects, PDFs, embeddings, instruments, and
CMCA authors in a structured, queryable schema supporting multi-user
audit workflows.

**Method:** PostgreSQL [@postgresql] with pgvector extension [@pgvector]
(Database/schema.sql:1-127).

**Key Tables:**

1.  **users** (line 5-11): `user_id`, `username` (unique),
    `password_hash`, `user_type` (admin/general_user), `created_at` -
    supports authentication and role-based access
2.  **projects** (line 13-18): `project_id`, `project_name` (unique),
    `created_by` (FK to users), `created_at` - organize PDFs by audit
    year/theme
3.  **pdfs** (line 20-42): `pdf_id`, `title`, `authors`, `affiliation`,
    `doi` (unique), `instruments_json` (JSONB), `num_pages`,
    `publish_date`, `uploaded_by` (FK), `project_id` (FK),
    `upload_date`, `cosine_similarity`, `cmca_result`, `storage_path` -
    stores metadata, LLM results, file path; indexes on `project_id`,
    `uploaded_by`, `doi` (line 36-38)
4.  **sentence_embeddings** (line 43-47): `id`, `sentence`, `embedding`
    (VECTOR(768)) - gold standard phrase embeddings for similarity
    search; requires pgvector extension
5.  **instruments** (line 52-55): `instrument_id`, `instrument_name`
    (unique) - instrument master list
6.  **cmca_authors** (line 58-67): `cmca_author_id`, `full_name`,
    `email` (unique) - CMCA staff/collaborator master list; index on
    `full_name` (line 66)

**Views:** - **v_pdf_cmca_matches** (line 99-115): Joins `pdf_authors`,
`pdfs`, `cmca_authors` on normalized name (remove punctuation,
lowercase) → identifies PDFs with CMCA authors -
**v_pdf_has_cmca_author** (line 118-126): Per-PDF flag ("Yes"/"No") for
CMCA author involvement

**Data Flow:** `PdfRepo.create()`
(src/backend/app/repositories/pdf_repo.py) inserts metadata into `pdfs`
table; `store_embedding.py` populates `sentence_embeddings` from
goldstandard.txt.

**Outputs:** Structured data queryable via API routes; supports
filtering by project, instruments, date, CMCA result.

**Migration Strategy:**  **TBD** - No Alembic migrations configured.
**TODO:** Add src/backend/app/db/migrations/ for schema versioning.

### 2.6 REST API

**Purpose:** Provide RESTful endpoints for authentication, project
management, PDF upload/review, and user management with JWT-based
security.

**Method:** FastAPI [@fastapi] with async SQLAlchemy
(src/backend/app/main.py:1-30, routers in src/backend/app/routers/).

**Key Routes:**

1.  **Health:** `GET /health` → `{"ok": true}` (line 15-17);
    `GET /health/db` → database connection check (line 19-25)
2.  **Authentication:** (routers/auth.py:7-17)
    -   `POST /auth/register` - payload:
        `{"username", "password", "user_type"}` → returns JWT token
    -   `POST /auth/login` - payload: `{"username", "password"}` →
        returns JWT token
3.  **Projects:** (routers/projects.py:27-98)
    -   `GET /projects` - list all projects (query params: `mine=true`,
        `limit`, `offset`)
    -   `POST /projects` - create project
    -   `PATCH /projects/{project_id}` - update name (admin/creator
        only)
    -   `DELETE /projects/{project_id}` - delete (admin/creator only,
        line 76-78 role check)
4.  **PDFs:** (routers/pdfs.py:31-170)
    -   `POST /pdfs/upload` - multipart form: `file`, `project_id`,
        optional overrides → returns `PdfOut` schema with `pdf_id`,
        `title`, `authors`, `doi`, `instruments_json`, `cmca_result`,
        `cosine_similarity`, `storage_path`
    -   `GET /pdfs` - list PDFs (query params: `project_id`, `limit`,
        `offset`)
    -   `GET /pdfs/{pdf_id}` - get metadata
    -   `GET /pdfs/{pdf_id}/file` - download PDF file (FileResponse with
        media type `application/pdf`)
    -   `PATCH /pdfs/{pdf_id}` - update metadata (line 114-145)
    -   `DELETE /pdfs/{pdf_id}` - delete record and file (line 147-170)

**Security:** All routes except `/auth/*` require JWT Bearer token
[@rfc7519] (routers/pdfs.py:20-29); dependency `get_actor_claims(token)`
decodes JWT, extracts `user_id`, `username`, `user_type`; token
expiration: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

**Key Parameters:** - JWT algorithm: HS256
(src/backend/app/core/config.py:20) - Token expiration: 60 minutes (line
18) - Pagination: default limit=50, max limit=200

**Commands to Run:**

``` bash
cd src/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs at <http://localhost:8000/docs>

**Outputs:** JSON responses per route; errors: 401 Unauthorized
(invalid/expired JWT), 404 Not Found, 409 Conflict (duplicate
project/DOI), 500 Internal Server Error (DB failure).

### 2.7 Web User Interface

**Purpose:** Provide a user-friendly interface for login, PDF upload,
project management, filtering, visualization, and review.

**Method:** Streamlit [@streamlit] 1.38.0 (cmca_app_2/app.py, pages in
cmca_app_2/pages/).

**Key Features:**

1.  **Login/Register:** (modules/login.py:10-145) Form inputs: username,
    password → `POST /auth/register` or `/auth/login` (line 75-104) →
    stores JWT token in `st.session_state["token"]` (line 93)
2.  **Dashboard:** (pages/dashboard.py:101-281)
    -   **Charts:** Pie chart: CMCA Yes/No distribution (Plotly donut,
        `hole=0.55`, line 112-144); bar chart: Top 5 instruments by PDF
        count
    -   **Upload Form:** File uploader (PDF only) + project dropdown →
        `POST /pdfs/upload` via `_api_upload_pdf()` (line 152-175)
    -   **Create Project:** Text input → `POST /projects` (line 177-197)
    -   **Filters:** Project dropdown (server-side `?project_id=`),
        instruments multiselect (client-side), sort by date/title (line
        212-219)
    -   **PDF Cards:** Title + CMCA badge (YES/NO), metadata (project,
        instruments, upload date dd-mm-yyyy), "Open" button → detail
        page (line 254-276)
3.  **Detail Page:** (pages/details.py) Display full metadata, scores;
    download button → `GET /pdfs/{pdf_id}/file`; edit form →
    `PATCH /pdfs/{pdf_id}`; delete button → `DELETE /pdfs/{pdf_id}`

**Commands to Run:**

``` bash
cd cmca_app_2
streamlit run app.py
```

Opens at <http://localhost:8501>

**Outputs:** Interactive web interface with visual feedback (charts
update on upload, filters applied instantly).

**Limitations:** Single-file upload only (no batch upload); no export
button (CSV/XLSX TBD); TinyDB fallback (core/db.py:7-135) stores data in
JSON file (`.cmca_store/cmca.json`), not shared with API database.

## 3. Discussion

### Comparison of Methods

**Heuristic Extraction vs. LLM Extraction:**

| Aspect | Heuristic (PyMuPDF) | LLM (GPT-4o) |
|-----------------|---------------------------------|----------------------|
| **Speed** | Fast (\~1-3s per PDF) | Slow (\~5-15s per sentence) |
| **Cost** | Free (local compute) | \$0.005 per sentence |
| **Accuracy** | High for standard layouts; fails on scanned/irregular PDFs | High for natural language understanding; robust to layout |
| **Scalability** | Excellent (no external API) | Limited by quota and rate limits |

**Decision:** Use heuristic extraction for metadata (title, authors,
DOI) and LLM for acknowledgement classification. This balances
throughput, cost, and accuracy.

**Embedding Similarity vs. Keyword Matching:**

| Aspect | Embedding Similarity | Keyword Matching |
|-----------------|------------------------------|--------------------------|
| **Semantic Understanding** | Yes (cosine similarity [@salton1975vector] captures meaning) | No (exact string match) |
| **Paraphrase Robustness** | Yes | No |
| **Latency** | \~1s per PDF (batch encoding) | \<100ms |

**Decision:** Use embedding similarity [@manning2008introduction] to
filter candidates before LLM, reducing false positives from keyword-only
approaches.

### Strengths

1.  **End-to-End Automation:** Single pipeline from PDF upload to
    annotated output; 10-30 seconds per PDF (QUICKSTART.md:317)
2.  **Multi-User Support:** User authentication, project organization,
    role-based access control (admin can delete any project/PDF; general
    users delete own uploads) (routers/projects.py:76-78)
3.  **Explainability:**
    -   Yellow highlights show LLM decisions in context
        (highlight_service.py:52-54)
    -   LLM prompt includes top similarity match for provenance
        (llm_service.py:20-21)
    -   "Reason" field in LLM response explains classification
        (llm_service.py:42)
4.  **Fallback Mechanisms:** GPT-3.5-turbo fallback on GPT-4o quota
    (llm_service.py:93-103); TinyDB fallback in Streamlit for standalone
    mode; unhighlighted PDF returned on highlighting errors
    (pdf_service.py:68-76)
5.  **Production-Ready Infrastructure:** Async FastAPI with connection
    pooling; PostgreSQL with pgvector; JWT authentication; structured
    error handling

### Limitations

1.  **Extraction Accuracy Depends on PDF Layout:** Two-column threshold
    (40px gap) may fail on narrow-margin or 3+ column layouts
    (extraction_service.py:73); misordered sentences reduce LLM
    accuracy. **Mitigation:**  TODO: Add adaptive threshold based on
    page width; support OCR for scanned PDFs.

2.  **Similarity Threshold Not Tuned:** Threshold 0.70
    (llm_service.py:46) is arbitrary; novel phrasing below threshold
    skipped by LLM. **Mitigation:**  TODO: Tune threshold on
    validation set with precision-recall curve; expand gold standard
    phrases.

3.  **English-Only Prompt:** LLM prompt (llm_service.py:13-43) is
    English-only; non-English acknowledgements misclassified.
    **Mitigation:**  TODO: Add language detection (langdetect),
    translate to English (Google Translate API), or use multilingual
    embeddings (multilingual-e5-base).

4.  **No CSV/XLSX Export:** Export functionality not implemented
    (README.md:318). **Mitigation:**  TODO: Add
    `GET /pdfs/export?format=csv&project_id=1` route in routers/pdfs.py;
    use pandas DataFrame.to_csv() or openpyxl.

5.  **Highlighting Fails on Multi-Line Sentences:** `page.search_for()`
    returns empty if sentence spans multiple lines with different
    whitespace/hyphenation (highlight_service.py:47-49); some verified
    sentences lack highlights. **Mitigation:** Current behavior logs
    warning;  TODO: Use fuzzy text search (regex with flexible
    whitespace) or bbox-based highlighting.

6.  **No Rate Limiting on OpenAI API:** Rapid uploads may exceed OpenAI
    rate limits; requests fail with RateLimitError. **Mitigation:**
    Fallback to GPT-3.5-turbo exists;  TODO: Add retry logic with
    exponential backoff (tenacity library) or local LLM (Llama-2).

### Explainability and Responsible Use

**Explainability:**

1.  **Visual Annotations:** Yellow highlights enable reviewers to
    quickly see which sentences triggered "Yes" classification
    (highlight_service.py:52-54)
2.  **Provenance in Prompt:** LLM prompt includes top similarity match +
    score (llm_service.py:20-21), showing why sentence was selected
3.  **Structured Output:** "Answer: Yes/No\nReason: ..." format
    (llm_service.py:40-42) provides human-readable justification
4.  **Sentence IDs:** Stable IDs (e.g., `p2_s12`) allow cross-reference
    between detail view and PDF

**Responsible Use:**

1.  **Gold Standard Curation:** Phrases in goldstandard.txt curated by
    CMCA domain experts familiar with acknowledgement norms, reducing
    reliance on potentially biased LLM training data
2.  **Constrained Entities:** LLM prompt explicitly constrains
    recognition to CMCA/UWA/Microscopy Australia/NCRIS
    (llm_service.py:24-28), preventing over-classification of generic
    thanks
3.  **Human-in-the-Loop:** Streamlit UI enables reviewers to verify,
    edit, or delete classifications; not fully automated
4.  **No Personal Data:** System processes publication metadata only; no
    sensitive data beyond author names (public information)

**Data Bias and Mitigation:**

1.  **Bias in Embeddings:** intfloat/e5-base-v2 [@wang2022e5] trained on
    web text, may under-represent domain-specific microscopy
    terminology; lower similarity scores for domain-specific phrasings.
    **Mitigation:** Gold standard [@gold_standard] includes
    microscopy-specific terms; periodic updates to goldstandard.txt
    based on false negatives.

2.  **Bias in LLM:** GPT-4o [@openai2023gpt4] trained on diverse text,
    may favor Western/English acknowledgement styles; non-Western or
    translated acknowledgements may be misclassified. **Mitigation:**
    Prompt specifies formal criteria (llm_service.py:30-38) to reduce
    stylistic bias;  TODO: Evaluate on multilingual test set.

3.  **Gold Standard Coverage:** goldstandard.txt may favor specific
    phrasing styles (e.g., "We acknowledge..." vs. "We thank...");
    phrases not in gold standard receive lower similarity scores.
    **Mitigation:** Expand gold standard iteratively by reviewing false
    negatives; use LLM to generate paraphrases for augmentation.

## 4. Conclusion

### Summary

This project successfully implements Stages 1 (API), 2A (Web GUI), and
2B (Advanced Web GUI) of the CMCA Publication Audit System
(README.md:15-23). The system delivers:

1.  **Automated PDF Processing:** PyMuPDF [@pymupdf] extraction +
    embedding similarity [@wang2022e5; @salton1975vector] + GPT-4o
    [@openai2023gpt4] classification pipeline processes PDFs in 10-30
    seconds
2.  **Multi-User Infrastructure:** FastAPI [@fastapi] backend with JWT
    auth [@rfc7519], PostgreSQL [@postgresql] database, role-based
    access control (src/backend/app/main.py, Database/schema.sql)
3.  **User-Friendly Interface:** Streamlit [@streamlit] web UI with
    charts, filters, upload forms, review workflows
    (cmca_app_2/pages/dashboard.py)
4.  **Explainable Results:** Yellow highlights and LLM reasoning enable
    human-in-the-loop verification (highlight_service.py,
    llm_service.py:40-42)
5.  **Production Readiness:** Async architecture, connection pooling,
    fallback mechanisms, error handling

### Key Risks and Constraints

1.  **OpenAI API Cost and Quota:** Cost scales linearly with PDFs;
    \$0.035 per PDF (GPT-4o) or \$0.0035 (GPT-3.5-turbo); large batches
    (1000 PDFs) cost \$35. **Mitigation:** Fallback to GPT-3.5-turbo
    exists;  TODO: Add local LLM option (Llama-2, Mistral) or caching
    for repeated queries.

2.  **Extraction Failures on Scanned PDFs:** Scanned PDFs without text
    layer return empty results; manual re-entry required.
    **Solution:** Integrate OCR (Tesseract, Google Vision
    API) with confidence thresholding.

3.  **No Password Policy or Security Audit:** Weak passwords may be set;
    JWT secret key default is insecure. **Mitigation:**  TODO: Enforce
    password complexity (passlib validators); rotate JWT_SECRET_KEY in
    production; add HTTPS termination.

### Future Improvements Mapped to Repository

1.  **OCR Support for Scanned PDFs** (extraction_service.py comments):
    Detect blank text layer → run Tesseract OCR → merge with extraction
    pipeline

2.  **Multi-Language Acknowledgements** (llm_service.py:13-43): Language
    detection (langdetect) → translate to English (Google Translate API)
    → embed and classify; alternative: multilingual embeddings
    (multilingual-e5-base) + multilingual LLM prompt

3.  **Batch Upload and Background Jobs**: API accepts multiple files →
    queues processing with Celery or FastAPI BackgroundTasks → returns
    job IDs → poll for completion; non-blocking uploads for large
    batches

4.  **Export with Filters** (routers/pdfs.py:170, dashboard.py:281):
    `GET /pdfs/export?format=csv&project_id=1&cmca_result=Yes&start_date=2024-01-01`
    → query database with filters → stream CSV/XLSX via
    StreamingResponse

5.  **Admin Dashboard for Gold Standard Management**: Web UI page for
    adding/editing/deleting gold standard phrases; new routes
    `POST /gold_standard`, `GET /gold_standard`,
    `DELETE /gold_standard/{id}`; re-run embedding on update

6.  **Similarity Threshold Tuning** (llm_service.py:46): Grid search on
    validation set with precision-recall curve; create
    src/tune_threshold.py to test thresholds 0.5-0.9 and compute F1

## A. Figures and Tables

### Figure A.1: System Architecture Diagram

``` mermaid
graph TB
    subgraph "User Interface"
        U[User/Researcher]
        WEB[Streamlit Web UI<br/>cmca_app_2/app.py]
        API_CLIENT[API Client<br/>curl/HTTP]
    end

    subgraph "API Layer"
        API[FastAPI REST API<br/>src/backend/app/main.py]
        AUTH[Auth Router<br/>/auth/register<br/>/auth/login]
        PDF_ROUTER[PDF Router<br/>/pdfs/upload<br/>/pdfs/{id}]
        PROJ_ROUTER[Project Router<br/>/projects]
    end

    subgraph "Service Layer"
        PDF_SVC[PDF Service<br/>pdf_service.py]
        EXTRACT[Extraction Service<br/>extraction_service.py<br/>PyMuPDF]
        LLM_SVC[LLM Service<br/>llm_service.py<br/>GPT-4o/GPT-3.5]
        SIM[Similarity Search<br/>similarity_search.py<br/>intfloat/e5-base-v2]
        HIGHLIGHT[Highlight Service<br/>highlight_service.py]
    end

    subgraph "Storage"
        DB[(PostgreSQL<br/>with pgvector)]
        FILES[File Storage<br/>UPLOAD_DIR]
        GOLD[Gold Standard<br/>docs/gold_standard/<br/>goldstandard.txt]
    end

    U -->|1. Upload PDF| WEB
    U -->|1. Upload PDF| API_CLIENT
    WEB -->|HTTP + JWT| API
    API_CLIENT -->|HTTP + JWT| API
    API --> AUTH
    API --> PDF_ROUTER
    API --> PROJ_ROUTER
    PDF_ROUTER -->|2. Ingest| PDF_SVC
    PDF_SVC -->|3. Extract text/metadata| EXTRACT
    PDF_SVC -->|4. Verify acknowledgements| LLM_SVC
    LLM_SVC -->|Embed sentences| SIM
    SIM -->|Query embeddings| DB
    DB -->|Top-k matches| SIM
    SIM -->|Filtered candidates| LLM_SVC
    LLM_SVC -->|GPT-4o API call| LLM_SVC
    PDF_SVC -->|5. Annotate PDF| HIGHLIGHT
    PDF_SVC -->|6a. Store metadata| DB
    PDF_SVC -->|6b. Store file| FILES
    GOLD -.->|Embedded via<br/>store_embedding.py| DB
    PDF_ROUTER -->|7. List/Get| DB
    PDF_ROUTER -->|Download| FILES
    WEB -->|Display charts/filters| WEB
    
    classDef userInterface fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef apiLayer fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef serviceLayer fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef storage fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    
    class U,WEB,API_CLIENT userInterface
    class API,AUTH,PDF_ROUTER,PROJ_ROUTER apiLayer
    class PDF_SVC,EXTRACT,LLM_SVC,SIM,HIGHLIGHT serviceLayer
    class DB,FILES,GOLD storage
```

**Source:** docs/architecture.mmd

### Figure A.2: Processing Pipeline Sequence

``` mermaid
sequenceDiagram
    actor User
    participant Web as Streamlit Web UI
    participant API as FastAPI /pdfs/upload
    participant PdfSvc as PdfService
    participant Extract as ExtractionService<br/>(PyMuPDF)
    participant LLM as LLMService<br/>(GPT-4o)
    participant Sim as SimilaritySearch<br/>(pgvector)
    participant DB as PostgreSQL
    participant Files as File Storage
    
    User->>Web: 1. Select PDF + Project
    Web->>API: 2. POST /pdfs/upload<br/>(multipart: file, project_id, JWT token)
    API->>PdfSvc: 3. ingest(file_bytes, uploaded_by, project_id)
    PdfSvc->>Extract: 4. extract_api(file_bytes)
    Extract->>Extract: Parse layout, extract metadata, segment sentences
    Extract-->>PdfSvc: 5. Return JSON {title, authors, doi, sentences}
    PdfSvc->>LLM: 6. run_llm_verification_from_json(extractor_json)
    LLM->>Sim: 7. search_sentences(sentences, k=30)
    Sim->>Sim: Embed sentences (intfloat/e5-base-v2)
    Sim->>DB: 8. Query sentence_embeddings (pgvector cosine similarity)
    DB-->>Sim: 9. Top-k matches per sentence
    Sim-->>LLM: 10. Return {sentence: [(match, score), ...]}
    LLM->>LLM: 11. Filter by threshold >= 0.70, rank, take top 7
    loop For each top candidate
        LLM->>LLM: 12. Build prompt with sentence + top match
        LLM->>LLM: 13. Call OpenAI API (GPT-4o, fallback to GPT-3.5)
        LLM->>LLM: 14. Parse "Answer: Yes/No"
    end
    LLM->>LLM: 15. Aggregate: any "Yes" → cmca_result="Yes"
    LLM-->>PdfSvc: 16. Return {cmca_result, cosine_similarity, Sentence_verifications}
    PdfSvc->>PdfSvc: 17. highlight_answer_yes_sentences (yellow annotations)
    PdfSvc->>Files: 18. Write highlighted PDF (UUID filename to UPLOAD_DIR)
    PdfSvc->>DB: 19. Insert pdfs record (metadata, cmca_result, storage_path)
    DB-->>PdfSvc: 20. Confirm insert (pdf_id)
    PdfSvc-->>API: 21. Return PdfOut schema
    API-->>Web: 22. HTTP 201 + JSON response
    Web-->>User: 23. Show success + PDF card
```

**Source:** docs/sequence.mmd

### Table A.1: Implementation Status by Component

| Component | Implementation | Evidence | Status |
|----------------|------------------------|----------------|----------------|
| PDF Extraction | PyMuPDF layout-aware parsing | src/backend/app/services/extraction_service.py:402-514 | Complete |
| Embedding Similarity | intfloat/e5-base-v2 + pgvector | src/backend/app/services/similarity_search.py:9-38 | Complete |
| LLM Verification | GPT-4o/GPT-3.5-turbo | src/backend/app/services/llm_service.py:46-127 | Complete |
| PDF Highlighting | PyMuPDF yellow annotations | src/backend/app/services/highlight_service.py:8-59 | Complete |
| Database | PostgreSQL + pgvector | Database/schema.sql:1-127 | Complete |
| REST API | FastAPI with JWT auth | src/backend/app/main.py, routers/ | Complete |
| Web UI | Streamlit with charts/filters | cmca_app_2/app.py, pages/ | Complete |
| Export | CSV/XLSX export | No export route in routers/pdfs.py |  TBD |
| Tests | Automated test suite | No tests/ directory |  TBD |

### Table A.2: Gold Standard Acknowledgement Phrases (Sample)

| Category | Example Phrases | Source |
|---------------------|---------------------------------|------------------|
| CMCA Direct | "Centre for Microscopy Characterisation and Analysis", "acknowledge CMCA", "technical assistance from CMCA" | docs/gold_standard/goldstandard.txt:1-24 |
| Microscopy Australia | "Microscopy Australia", "Microscopy Australia UWA node", "supported by Microscopy Australia" | docs/gold_standard/goldstandard.txt:4-42 |
| NCRIS | "National Collaborative Research Infrastructure Strategy", "funded by NCRIS", "NCRIS Microscopy Australia" | docs/gold_standard/goldstandard.txt:25,43-44 |
| UWA Facilities | "University of Western Australia microscopy facility", "UWA microscopy centre" | docs/gold_standard/goldstandard.txt:7-9 |

**Total Phrases:** 44 (embedded as 768-dimensional vectors in
sentence_embeddings table)

### Table A.3: Key Parameters and Configuration

| Parameter | Value | Location | Rationale |
|-------------------|-----------------|-----------------|-------------------|
| Two-column threshold | 40px gap | extraction_service.py:73 | Tuned for typical two-column journal layouts |
| Similarity threshold | 0.70 | llm_service.py:46 | Balances precision/recall to reduce false positives |
| LLM top-k candidates | 7 | llm_service.py:46 | Limits API costs while maintaining recall |
| Embedding model | intfloat/e5-base-v2 | similarity_search.py:6 | 768-dim, state-of-art sentence embeddings |
| LLM model | GPT-4o, fallback GPT-3.5-turbo | llm_service.py:86,97 | High accuracy with cost-effective fallback |
| LLM temperature | 0.0 | llm_service.py:91 | Deterministic output for reproducibility |
| JWT expiration | 60 minutes | config.py:18 | Balance security and user convenience |
| Pagination limit | 50 (default), 200 (max) | routers/pdfs.py:63,90 | Balance response size and performance |

------------------------------------------------------------------------

## References

All claims in this report are grounded in repository files at commit
state (main branch) and cited academic literature. Technical citations
follow standard academic format with BibTeX references defined in
`docs/report/refs.bib`.

### Academic and Technical References

1.  **Brown, T., Mann, B., Ryder, N., et al.** (2020). Language Models
    are Few-Shot Learners. *Advances in Neural Information Processing
    Systems*, 33, 1877-1901.

2.  **Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K.** (2019). BERT:
    Pre-training of Deep Bidirectional Transformers for Language
    Understanding. *Proceedings of NAACL-HLT 2019*, 4171-4186.
    <doi:10.18653/v1/N19-1423>

3.  **Johnson, J., Douze, M., & Jégou, H.** (2019). Billion-scale
    Similarity Search with GPUs. *IEEE Transactions on Big Data*, 7(3),
    535-547. <doi:10.1109/TBDATA.2019.2921572>

4.  **Jones, M., Bradley, J., & Sakimura, N.** (2015). JSON Web Token
    (JWT). RFC 7519, IETF. <https://www.rfc-editor.org/rfc/rfc7519.txt>

5.  **Manning, C. D., Raghavan, P., & Schütze, H.** (2008).
    *Introduction to Information Retrieval*. Cambridge University Press.

6.  **OpenAI** (2023). GPT-4 Technical Report. arXiv preprint
    arXiv:2303.08774. <https://arxiv.org/abs/2303.08774>

7.  **Reimers, N., & Gurevych, I.** (2019). Sentence-BERT: Sentence
    Embeddings using Siamese BERT-Networks. *Proceedings of EMNLP-IJCNLP
    2019*, 3982-3992. <doi:10.18653/v1/D19-1410>

8.  **Salton, G., Wong, A., & Yang, C.-S.** (1975). A Vector Space Model
    for Automatic Indexing. *Communications of the ACM*, 18(11),
    613-620. <doi:10.1145/361219.361220>

9.  **Wang, L., Nan, N., Yang, X., et al.** (2022). Text Embeddings by
    Weakly-Supervised Contrastive Pre-training. arXiv preprint
    arXiv:2212.03533.

### Software and Framework References

10. **Artifex Software** (2025). PyMuPDF (fitz): PDF parsing and text
    extraction library. Used in
    src/backend/app/services/extraction_service.py

11. **Australian Government Department of Education** (2023). National
    Collaborative Research Infrastructure Strategy (NCRIS).
    <https://www.education.gov.au/ncris>

12. **Microscopy Australia** (2024). National Microscopy Research
    Facility. <https://www.microscopy.org.au/>

13. **OpenAI** (2024). GPT-4o: OpenAI's Multimodal Language Model.
    OpenAI API. Used in src/backend/app/services/llm_service.py

14. **PostgreSQL Global Development Group** (1996-2025). PostgreSQL: The
    World's Most Advanced Open Source Relational Database.
    <https://www.postgresql.org/>

15. **Ramírez, S.** (2018-2025). FastAPI: Modern, fast
    (high-performance) web framework. <https://fastapi.tiangolo.com/>

16. **Streamlit Inc.** (2019-2025). Streamlit: The fastest way to build
    data apps. <https://streamlit.io/>

17. **Kane, A.** (2021-2025). pgvector: Open-source vector similarity
    search for Postgres. <https://github.com/pgvector/pgvector>

### Internal Repository Evidence Sources

-   README.md - Installation, usage, feature matrix
-   ARCHITECTURE.md - System design, pipeline narrative
-   QUICKSTART.md - Setup guide, processing timeline
-   REPORT_SECTIONS.md - Methods, results, discussion
-   Database/schema.sql - Database schema with pgvector (lines 1-127)
-   docs/gold_standard/goldstandard.txt - 44 curated acknowledgement
    phrases
-   docs/architecture.mmd, docs/sequence.mmd - Mermaid diagram sources
-   src/backend/app/services/extraction_service.py - PDF extraction
    (lines 402-514)
-   src/backend/app/services/llm_service.py - LLM verification (lines
    46-127)
-   src/backend/app/services/similarity_search.py - Embedding similarity
    (lines 9-38)
-   src/backend/app/services/highlight_service.py - PDF highlighting
    (lines 8-59)
-   src/backend/app/main.py - FastAPI entry point (lines 1-30)
-   src/backend/app/routers/ - API route implementations
-   cmca_app_2/app.py - Streamlit web UI entry point
-   cmca_app_2/pages/dashboard.py - Dashboard with charts/filters (lines
    101-281)


