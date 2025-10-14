# CMCA Publication Audit System

A semi-automated system for auditing scientific publications that acknowledge or involve CMCA (Centre for Microscopy Characterisation and Analysis) and Microscopy Australia facilities. The system ingests PDFs, extracts metadata and acknowledgements, scores relevance using embedding similarity and LLM verification, and provides a web interface for review and management.

## Project Goal

Automate the annual CMCA publication audit by: - Ingesting scientific publication PDFs - Extracting acknowledgements, authors, affiliations, and instrument mentions - Scoring acknowledgement relevance to CMCA/Microscopy Australia/UWA - Storing results in a structured database - Providing review workflows through Web UI and API - Exporting audit results

## Feature Matrix by Stage

| Stage | Description | Status | Evidence |
|----|----|----|----|
|  |  |  |  |
| **1B** | FastAPI backend | ✅ Implemented | `src/backend/app/main.py`, routers in `src/backend/app/routers/` |
| **2A** | Basic Web GUI (Streamlit) | ✅ Implemented | `cmca_app_2/app.py` with TinyDB fallback |
| **2B** | Advanced Web GUI | ✅ Implemented | User auth, projects, review workflow in `cmca_app_2/pages/`, API integration |

**Implemented:** - ✅ FastAPI REST API with JWT authentication - ✅ PostgreSQL database with pgvector extension for embeddings - ✅ PDF text extraction (PyMuPDF) with layout handling and metadata parsing - ✅ Sentence-level embedding similarity search against gold standard phrases - ✅ LLM-based acknowledgement verification (OpenAI GPT-4o/GPT-3.5-turbo) - ✅ PDF highlighting of verified acknowledgement sentences - ✅ Streamlit web UI with user management, project organization, filtering, charts - ✅ Multi-user support with admin and general user roles

**TBD:** - CSV/XLSX export functionality - Automated tests

## Tech Stack

**Backend:** - Python 3.10+ - FastAPI (REST API framework) - SQLAlchemy + asyncpg (async PostgreSQL ORM) - PostgreSQL 15+ with pgvector extension - PyMuPDF (fitz) for PDF parsing - sentence-transformers (intfloat/e5-base-v2) for embeddings - OpenAI API (GPT-4o, GPT-3.5-turbo fallback) - spaCy (en_core_web_trf) for NER in `src/match.py` - python-jose for JWT tokens - psycopg2 for synchronous database operations in embedding scripts

**Frontend:** - Streamlit 1.38.0 - Plotly for charts - TinyDB (lightweight JSON database for standalone mode)

**Database:** - PostgreSQL with pgvector extension (vector similarity search) - Schema: users, projects, pdfs, sentence_embeddings, instruments, cmca_authors, gold_standards

## Prerequisites

-   Python 3.10 or higher
-   PostgreSQL 15 or higher with pgvector extension installed
-   OpenAI API key (for GPT-4o/GPT-3.5-turbo)
-   2GB+ RAM (for embedding model)

## Repository Structure

```         
cmca-publication-audit-main/
├── cmca_app_2/                  # Streamlit web UI (Stage 2A/2B)
│   ├── app.py                   # Main Streamlit entry point
│   ├── core/                    # State, session, API client, TinyDB
│   ├── modules/                 # Login UI components
│   ├── pages/                   # Dashboard, PDF details pages
│   └── requirements.txt         # UI dependencies
├── Database/
│   ├── schema.sql               # Complete PostgreSQL schema
│   └── README.md                # Database setup notes
├── docs/
│   └── gold_standard/
│       ├── goldstandard.txt     # Gold standard acknowledgement phrases
│       ├── Gold_Standard_v1.xlsx
│       └── Gold_Standard_Codebook_v2.docx
├── src/
│   ├── backend/
│   │   └── app/
│   │       ├── main.py          # FastAPI application entry point
│   │       ├── core/            # Config, security utilities
│   │       ├── db/              # Database session, base models
│   │       ├── models/          # SQLAlchemy ORM models
│   │       ├── repositories/    # Data access layer
│   │       ├── routers/         # API route handlers (auth, pdfs, projects, users)
│   │       ├── schemas/         # Pydantic request/response schemas
│   │       └── services/        # Business logic (extraction, LLM, similarity, highlight)
│   ├── match.py                 # Staff/instrument mention detection (spaCy NER)
│   └── store_embedding.py       # Script to populate sentence_embeddings table
└── README.md                    # This file
```

## Quick Start

**For detailed installation:** See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) (30-minute comprehensive setup)\
**For experienced users:** See [QUICKSTART.md](QUICKSTART.md) (10-minute rapid setup)

### Prerequisites

-   Python 3.10 or higher
-   PostgreSQL 15+ with pgvector extension
-   OpenAI API key
-   20 GB free disk space

### Installation Overview

1.  Clone repository and create virtual environment
2.  Install Python dependencies (backend + frontend)
3.  Setup PostgreSQL database and pgvector extension
4.  Populate gold standard embeddings
5.  Configure environment variables (copy `env.template` to `.env`)
6.  Start API server and Web UI

**Detailed instructions:** [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)

## Configuration

All configuration is managed via environment variables.

**Setup:** Copy `env.template` to `.env` and fill in your values:

``` bash
cp env.template .env
# Edit .env with your database password and OpenAI API key
```

**For detailed configuration options:** See [INSTALLATION_GUIDE.md - Step 8](INSTALLATION_GUIDE.md#step-8-configure-environment-variables)\
**For environment variable reference:** See `src/backend/app/core/config.py`

## Usage

### API Server

**Start the FastAPI backend:**

``` bash
cd src/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive documentation (Swagger UI) at `http://localhost:8000/docs`.

#### API Endpoints

**Health:** - `GET /health` - Basic health check - `GET /health/db` - Database connection check

**Authentication:** - `POST /auth/register` - Register new user

````         
``` bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass", "user_type": "general_user"}'
```

Response: `{"access_token": "...", "token_type": "bearer"}`
````

-   `POST /auth/login` - Login and get JWT token

    ``` bash
    curl -X POST http://localhost:8000/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username": "testuser", "password": "testpass"}'
    ```

**Projects:** - `GET /projects` - List all projects (supports `?mine=true&limit=50&offset=0`) - `POST /projects` - Create new project `bash   curl -X POST http://localhost:8000/projects \     -H "Authorization: Bearer YOUR_TOKEN" \     -H "Content-Type: application/json" \     -d '{"project_name": "2025 Publications"}'` - `PATCH /projects/{project_id}` - Update project name - `DELETE /projects/{project_id}` - Delete project (admin or creator only)

**PDFs:** - `POST /pdfs/upload` - Upload and process PDF `bash   curl -X POST http://localhost:8000/pdfs/upload \     -H "Authorization: Bearer YOUR_TOKEN" \     -F "file=@sample.pdf" \     -F "project_id=1"` Returns: PDF metadata including `pdf_id`, `title`, `authors`, `doi`, `instruments_json`, `cmca_result` ("Yes"/"No"), `cosine_similarity`, `storage_path`

-   `GET /pdfs` - List PDFs (supports `?project_id=1&limit=50&offset=0`)
-   `GET /pdfs/{pdf_id}` - Get PDF metadata
-   `GET /pdfs/{pdf_id}/file` - Download PDF file (with highlights)
-   `PATCH /pdfs/{pdf_id}` - Update PDF metadata
-   `DELETE /pdfs/{pdf_id}` - Delete PDF record and file

**Users:** - `GET /users/me` - Get current user info - `GET /users` - List all users (pagination supported)

See `src/backend/app/routers/` for full route implementations.

### Web UI

**Start the Streamlit application:**

``` bash
cd cmca_app_2
streamlit run app.py
```

The web UI will open in your browser at `http://localhost:8501`.

**Features:** - **Login/Register**: Create account or sign in (`modules/login.py`) - **Dashboard** (`pages/dashboard.py`): - Upload PDFs (with project assignment) - Create projects - View pie chart (CMCA Yes/No) and bar chart (top instruments) - Filter by project, instruments; sort by date or title - List all PDFs with metadata cards - **PDF Details** (`pages/details.py`): - View extracted metadata, instruments, CMCA result, cosine similarity - Download highlighted PDF - Edit metadata - Delete PDF

**Default credentials:** Register a new account via the UI. No seed users are provided.

## Data Input/Output

### Input

-   **PDFs:** Upload via Web UI (`pages/dashboard.py:153-175`) or API (`POST /pdfs/upload`, `routers/pdfs.py:31-58`)
-   **Gold Standard Phrases:** Text file at `docs/gold_standard/goldstandard.txt`, loaded into `sentence_embeddings` table via `src/store_embedding.py`

### Storage

-   **PDF Files:** Saved to `UPLOAD_DIR` (default `storage/pdfs/`) with UUID filenames, annotated with yellow highlights on verified acknowledgement sentences
-   **Metadata:** PostgreSQL `pdfs` table (see `Database/schema.sql:20-42`, model at `src/backend/app/models/pdf.py`)
-   **Embeddings:** `sentence_embeddings` table (768-dimensional vectors from intfloat/e5-base-v2)

### Output

-   **API Responses:** JSON with extracted metadata (`title`, `authors`, `doi`, `instruments_json`, `num_pages`, `publish_date`, `cosine_similarity`, `cmca_result`)
-   **Highlighted PDF:** Download via Web UI or `GET /pdfs/{pdf_id}/file`
-   **CSV/XLSX Export:** **TBD** - Not yet implemented. TODO: Add export route in `src/backend/app/routers/pdfs.py`

## Processing Pipeline

1.  **Upload:** User uploads PDF via Web or API
2.  **Extract:** `extraction_service.py:402-514` parses PDF using PyMuPDF:
    -   Text extraction with 1/2-column layout detection (`extraction_service.py:45-101`)
    -   Title and authors via font size heuristics (`extraction_service.py:164-266`)
    -   DOI and year via regex (`extraction_service.py:106-107`)
    -   Instrument keywords (`extraction_service.py:270-287`)
    -   Sentence segmentation (`extraction_service.py:297-325`)
3.  **Score:** `llm_service.py:46-127` verifies acknowledgements:
    -   Embed sentences with intfloat/e5-base-v2
    -   Cosine similarity search against gold standard (`similarity_search.py:9-38`)
    -   Filter by threshold (0.70)
    -   LLM classification (GPT-4o, fallback to GPT-3.5-turbo on quota, `llm_service.py:84-103`)
4.  **Highlight:** `highlight_service.py:8-59` annotates "Answer: Yes" sentences in yellow
5.  **Store:** Save metadata to `pdfs` table, file to `UPLOAD_DIR` (`pdf_service.py:78-102`)
6.  **Review:** View in Streamlit dashboard or query via API

## License

**TBD:** No LICENSE file present. TODO: Add LICENSE file at repository root.

## Citation

**TBD:** Citation information not provided in repository.

## Contributing

This is a capstone project. Contribution guidelines TBD.

------------------------------------------------------------------------

## Documentation Guide

This project includes comprehensive documentation for different audiences and purposes:

### Getting Started

-   [**QUICKSTART.md**](QUICKSTART.md) - 10-minute rapid setup guide for experienced users
-   [**INSTALLATION_GUIDE.md**](INSTALLATION_GUIDE.md) - 30-minute comprehensive installation guide with troubleshooting

### Technical Documentation

-   [**ARCHITECTURE.md**](ARCHITECTURE.md) - System architecture, data flow, and technical design decisions
-   [**SOFTWARE_DEPENDENCIES.md**](SOFTWARE_DEPENDENCIES.md) - Complete dependency specification, installation, and troubleshooting
-   [**REQUIREMENTS.md**](REQUIREMENTS.md) - Full system requirements specification (business, functional, non-functional)

### Project Documentation

-   [**REPORT_SECTIONS.md**](REPORT_SECTIONS.md) - Project report with methods, results, discussion, and conclusions
-   [**env.template**](env.template) - Environment configuration template

### Recommended Reading Order

**For First-Time Setup:** 1. Read Prerequisites in this README 2. Follow [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) step-by-step 3. Review [QUICKSTART.md](QUICKSTART.md) for usage examples

**For Development:** 1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design 2. Check [SOFTWARE_DEPENDENCIES.md](SOFTWARE_DEPENDENCIES.md) for dependency details 3. Refer to [REQUIREMENTS.md](REQUIREMENTS.md) for specifications

### Support and Help

-   See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for setup guidance
-   See [SOFTWARE_DEPENDENCIES.md](SOFTWARE_DEPENDENCIES.md) for dependency details

------------------------------------------------------------------------

**Last Updated:** Generated from repository state (main branch)
