# Software Dependencies Specification

# CMCA Publication Audit System

**Document Version:** 1.0\
**Date:** October 14, 2025\
**Last Updated:** October 14, 2025

------------------------------------------------------------------------

## Table of Contents

1.  [System Requirements](#1-system-requirements)
2.  [Python Dependencies](#2-python-dependencies)
3.  [Database Requirements](#3-database-requirements)
4.  [External Services](#4-external-services)
5.  [Development Tools](#5-development-tools)
6.  [Installation Instructions](#6-installation-instructions)
7.  [Dependency Graph](#8-dependency-graph)
8.  [Security Considerations](#9-security-considerations)

------------------------------------------------------------------------

## 1. System Requirements

### 1.1 Operating System

**Supported Platforms:** - **Windows:** Windows 10 (build 19041) or later - **macOS:** macOS 11 (Big Sur) or later - **Linux:** Ubuntu 20.04 LTS, Debian 11, CentOS 8, or equivalent

**Minimum Requirements:** - **CPU:** 4 cores (Intel i5/AMD Ryzen 5 or better) - **RAM:** 8 GB minimum, 16 GB recommended - **Storage:** 20 GB free space (10 GB for models, 5 GB for PDFs, 5 GB for database) - **Network:** Stable internet connection (for OpenAI API and model downloads)

**Recommended Requirements:** - **CPU:** 8 cores with AVX2 support - **RAM:** 16 GB or more - **GPU:** Optional (CUDA-enabled PyTorch supported) - **Storage:** 50 GB SSD

### 1.2 Runtime Environment

**Python:** - **Version:** Python 3.10 or 3.11 (3.12 not yet tested) - **Distribution:** CPython (official Python distribution) - **Virtual Environment:** venv or conda

**Note:** Python 3.9 and earlier are NOT supported due to reliance on `typing` features (e.g., `str | None` syntax).

------------------------------------------------------------------------

## 2. Python Dependencies

### 2.1 Backend Dependencies

**Location:** `src/backend/requirements.txt`

#### 2.1.1 Core Web Framework

| Package | Version | Purpose | License |
|----|----|----|----|
| `fastapi` | 0.104.1 | REST API framework with async support | MIT |
| `uvicorn[standard]` | 0.24.0 | ASGI server with websocket and HTTP/2 support | BSD-3-Clause |
| `python-multipart` | 0.0.6 | Multipart form data parsing (file uploads) | Apache-2.0 |

**Key Features:** - Async/await support for high concurrency - Automatic OpenAPI documentation generation - Pydantic integration for request/response validation

#### 2.1.2 Database & ORM

| Package | Version | Purpose | License |
|----|----|----|----|
| `sqlalchemy` | 2.0.23 | Async ORM with PostgreSQL support | MIT |
| `asyncpg` | 0.29.0 | Async PostgreSQL driver (used by FastAPI) | Apache-2.0 |
| `psycopg2-binary` | 2.9.9 | Sync PostgreSQL driver (used by embedding scripts) | LGPL |
| `alembic` | 1.12.1 | Database migration tool (optional, for future use) | MIT |

**Important:** - `asyncpg` is used in FastAPI backend for async database operations - `psycopg2-binary` is used in `store_embedding.py` and `similarity_search.py` (synchronous operations) - Both drivers connect to the same PostgreSQL database

#### 2.1.3 Data Validation

| Package             | Version | Purpose                                 | License |
|---------------------|---------|-----------------------------------------|---------|
| `pydantic`          | 2.8.2   | Data validation and settings management | MIT     |
| `pydantic-settings` | 2.1.0   | Environment variable management         | MIT     |

**Usage:** - Request/response schemas in `src/backend/app/schemas/` - Configuration in `src/backend/app/core/config.py`

#### 2.1.4 Authentication & Security

| Package | Version | Purpose | License |
|----|----|----|----|
| `python-jose[cryptography]` | 3.3.0 | JWT token encoding/decoding | MIT |
| `passlib[bcrypt]` | 1.7.4 | Password hashing with bcrypt | BSD |
| `python-dotenv` | 1.0.0 | Load environment variables from .env | BSD-3-Clause |

**Security Notes:** - `passlib[bcrypt]` includes bcrypt backend for password hashing (cost factor 12) - `python-jose[cryptography]` includes cryptography backend for JWT signing (HS256 algorithm) - Never use default `JWT_SECRET_KEY` in production

#### 2.1.5 PDF Processing

| Package   | Version | Purpose                                  | License  |
|-----------|---------|------------------------------------------|----------|
| `PyMuPDF` | 1.23.8  | PDF parsing, text extraction, annotation | AGPL-3.0 |

**Also known as:** `fitz` (import name)

**Features Used:** - Text extraction with layout awareness (`page.get_text("blocks")`) - Bounding box analysis for column detection - Yellow highlight annotation (`page.add_highlight_annot()`) - PDF saving with compression (`save(garbage=4, deflate=True)`)

**License Note:** PyMuPDF uses AGPL-3.0 license. If deploying as a commercial service, consider licensing implications or alternative libraries (e.g., `pypdf`, `pdfplumber`).

#### 2.1.6 Machine Learning & NLP

| Package | Version | Purpose | License |
|----|----|----|----|
| `sentence-transformers` | 2.2.2 | Sentence embedding model (intfloat/e5-base-v2) | Apache-2.0 |
| `openai` | 1.3.0 | OpenAI API client (GPT-4o, GPT-3.5-turbo) | MIT |
| `torch` | 2.1.1 | PyTorch (backend for sentence-transformers) | BSD-3-Clause |
| `transformers` | 4.35.2 | Hugging Face transformers library | Apache-2.0 |

**Model Downloads:** - **intfloat/e5-base-v2:** \~700 MB (downloaded from Hugging Face on first use) - **Cache Location:** `~/.cache/torch/sentence_transformers/` or `~/.cache/huggingface/`

**GPU Support (Optional):** If you have an NVIDIA GPU, install a CUDA-enabled PyTorch build (see PyTorch install selector).

**OpenAI API:** - Requires API key from <https://platform.openai.com/> - Cost: \~\$0.035 per PDF (GPT-4o) or \~\$0.0035 (GPT-3.5-turbo)

#### 2.1.7 Optional: NER Matching

| Package | Version | Purpose | License |
|----|----|----|----|
| `spacy` | 3.7.2 | Named Entity Recognition (used in `src/match.py`) | MIT |
| `rapidfuzz` | 3.5.2 | Fuzzy string matching | MIT |
| `en_core_web_trf` | 3.7.0 | spaCy transformer model (560 MB) | MIT |

**Status:** Optional, not required for core functionality. Used only in `src/match.py` for staff/instrument mention detection.

**Installation:**

``` bash
pip install spacy==3.7.2 rapidfuzz==3.5.2
python -m spacy download en_core_web_trf
```

### 2.2 Frontend Dependencies

**Location:** `cmca_app_2/requirements.txt`

| Package     | Version | Purpose                                   | License    |
|-------------|---------|-------------------------------------------|------------|
| `streamlit` | 1.38.0  | Web UI framework                          | Apache-2.0 |
| `tinydb`    | 4.8.0   | Lightweight JSON database (fallback mode) | MIT        |
| `pydantic`  | 2.8.2   | Data validation                           | MIT        |
| `plotly`    | 5.23.0  | Interactive charts (pie, bar)             | MIT        |

**Additional Dependencies (auto-installed):** - `requests` - HTTP client for API calls - `pandas` - Data manipulation (used by Plotly) - `numpy` - Numerical operations

### 2.3 Development Dependencies (Optional)

**Not yet included in project:**

| Package          | Version | Purpose                           |
|------------------|---------|-----------------------------------|
| `pytest`         | 7.4.3   | Testing framework                 |
| `pytest-asyncio` | 0.21.1  | Async test support                |
| `httpx`          | 0.25.2  | Async HTTP client for API testing |
| `black`          | 23.11.0 | Code formatter                    |
| `ruff`           | 0.1.6   | Fast linter                       |
| `mypy`           | 1.7.0   | Static type checker               |

 

------------------------------------------------------------------------

## 3. Database Requirements

### 3.1 PostgreSQL

**Version:** PostgreSQL 15.0 or later (tested on 15.x)

**Installation:** See INSTALLATION_GUIDE for platform-specific steps, or the official PostgreSQL downloads page.

### 3.2 pgvector Extension

**Version:** pgvector 0.5.0 or later

**Purpose:** Vector similarity search for sentence embeddings (768-dimensional vectors)

**Installation:** See INSTALLATION_GUIDE for platform-specific steps, or the pgvector README for your platform.

**Enable in Database:**

``` sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Verify Installation:**

``` sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 3.3 Database Configuration

**Connection String Format:**

```         
postgresql+asyncpg://username:password@host:port/database_name
```

**Example:**

```         
postgresql+asyncpg://postgres:MyPassword@localhost:5432/cmca_audit
```

**Required Settings:** - **Max Connections:** 100 (default is sufficient) - **Shared Buffers:** 256 MB or more - **Work Memory:** 16 MB or more

**Schema Initialization:**

``` bash
createdb cmca_audit
psql -d cmca_audit -f Database/schema.sql
```

------------------------------------------------------------------------

## 4. External Services

### 4.1 OpenAI API

**Service:** OpenAI GPT Models\
**Endpoint:** <https://api.openai.com/v1/>\
**Authentication:** API Key

**Required Models:** - **Primary:** GPT-4o (`gpt-4o`) - **Fallback:** GPT-3.5-turbo (`gpt-3.5-turbo`)

**API Key Setup:** 1. Create account at <https://platform.openai.com/> 2. Generate API key at <https://platform.openai.com/api-keys> 3. Set environment variable: `bash    export OPENAI_API_KEY="sk-..."`

**Cost Estimates (as of Oct 2025):** - **GPT-4o:** \$0.005 per 1K input tokens, \$0.015 per 1K output tokens - **GPT-3.5-turbo:** \$0.0005 per 1K input tokens, \$0.0015 per 1K output tokens - **Typical PDF:** \~200 input tokens, \~50 output tokens per sentence - **Per PDF:** 7 sentences × \$0.005 ≈ \$0.035 (GPT-4o) or \$0.0035 (GPT-3.5-turbo)

**Rate Limits:** - Tier 1: 500 RPM (requests per minute), 100,000 TPM (tokens per minute) - Monitor usage at <https://platform.openai.com/usage>

**Error Handling:** - System automatically falls back to GPT-3.5-turbo on `RateLimitError` - Logs include model used for each verification

### 4.2 Hugging Face Model Hub

**Service:** Model repository for intfloat/e5-base-v2\
**Endpoint:** <https://huggingface.co/>\
**Authentication:** None required for public models

**Model Details:** - **Model ID:** `intfloat/e5-base-v2` - **Size:** \~700 MB - **Architecture:** BERT-based encoder (768-dimensional embeddings) - **License:** MIT - **Download:** Automatic on first use via `sentence-transformers` library

**Cache Location:** - **Linux/macOS:** `~/.cache/huggingface/hub/` - **Windows:** `C:\Users\{Username}\.cache\huggingface\hub\`

**Offline Mode:** If internet unavailable after initial download:

``` python
os.environ['TRANSFORMERS_OFFLINE'] = '1'
```

------------------------------------------------------------------------

## 5. Development Tools

### 5.1 Version Control

**Git:** Version 2.30 or later

**Installation:** - **Windows:** <https://git-scm.com/download/win> - **macOS:** `brew install git` or Xcode Command Line Tools - **Linux:** `sudo apt install git`

**Repository:**

``` bash
git clone <repository-url>
cd cmca-publication-audit-main
```

### 5.2 Python Virtual Environment

**venv (Recommended):**

``` bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

**conda (Alternative):**

``` bash
conda create -n cmca python=3.10
conda activate cmca
```

### 5.3 IDE/Editor (Optional)

Use any modern Python IDE/editor (e.g., VS Code or PyCharm); enable Python linting/formatting extensions as preferred.

------------------------------------------------------------------------

## 6. Installation Instructions

### 6.1 Quick Start (5 Minutes)

**Prerequisites:** - Python 3.10+ installed - PostgreSQL 15+ installed with pgvector - OpenAI API key

**Steps:**

1.  **Clone Repository:**

    ``` bash
    git clone <repository-url>
    cd cmca-publication-audit-main
    ```

2.  **Create Virtual Environment:**

    ``` bash
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    ```

3.  **Install Backend Dependencies:**

    ``` bash
    cd src/backend
    pip install -r requirements.txt
    ```

4.  **Install Frontend Dependencies:**

    ``` bash
    cd ../../cmca_app_2
    pip install -r requirements.txt
    ```

5.  **Setup Database:**

    ``` bash
    createdb cmca_audit
    psql -d cmca_audit -f ../Database/schema.sql
    psql -d cmca_audit -c "CREATE EXTENSION IF NOT EXISTS vector;"
    ```

6.  **Populate Embeddings:**

    ``` bash
    cd ../src
    # Edit store_embedding.py lines 21-26 with your DB credentials
    python store_embedding.py
    ```

7.  **Configure Environment:**

    ``` bash
    cd ..
    cat > .env << EOF
    DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/cmca_audit
    OPENAI_API_KEY=sk-your-api-key-here
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    UPLOAD_DIR=storage/pdfs
    EOF
    ```

8.  **Start Services:**

    ``` bash
    # Terminal 1: API
    cd src/backend
    uvicorn app.main:app --reload --port 8000

    # Terminal 2: Web UI
    cd cmca_app_2
    streamlit run app.py
    ```

9.  **Verify:**

    -   API: <http://localhost:8000/health> → `{"ok": true}`
    -   Web UI: <http://localhost:8501> → Login page

### 6.2 Detailed Installation (With Verification)

#### Step 1: Verify Python Version

``` bash
python --version  # Should show 3.10.x or 3.11.x
```

If using older Python, install Python 3.10: - **Windows:** <https://www.python.org/downloads/> - **macOS:** `brew install python@3.10` - **Linux:** `sudo apt install python3.10 python3.10-venv`

#### Step 2: Verify PostgreSQL Installation

``` bash
psql --version  # Should show 15.x or later
```

#### Step 3: Verify pgvector Installation

``` bash
psql -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

Should return a row with `vector` extension.

#### Step 4: Install Python Dependencies with Verification

``` bash
cd src/backend
pip install -r requirements.txt

# Verify installations
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy: {sqlalchemy.__version__}')"
python -c "import fitz; print(f'PyMuPDF: {fitz.__version__}')"
python -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers OK')"
python -c "import openai; print(f'OpenAI: {openai.__version__}')"
```

#### Step 5: Download Embedding Model (First Time Only)

``` bash
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('intfloat/e5-base-v2'); print('Model downloaded')"
```

This downloads \~700 MB to `~/.cache/huggingface/`.

#### Step 6: Test Database Connection

``` bash
psql -d cmca_audit -c "SELECT 1;"
```

Should return `1`.

------------------------------------------------------------------------

## 8. Dependency Graph

### 8.1 Backend Dependency Tree

```         
fastapi (API framework)
├── pydantic (validation)
├── starlette (ASGI toolkit)
└── uvicorn (ASGI server)
    └── uvloop (event loop, optional)

sqlalchemy (ORM)
├── asyncpg (async PostgreSQL driver)
└── psycopg2-binary (sync PostgreSQL driver, separate usage)

sentence-transformers (embeddings)
├── torch (PyTorch)
├── transformers (Hugging Face)
├── numpy
└── scikit-learn

openai (LLM API)
└── httpx (HTTP client)

pymupdf (PDF processing)
└── [no dependencies]

python-jose (JWT)
├── cryptography
└── ecdsa

passlib (password hashing)
└── bcrypt
```

### 8.2 Frontend Dependency Tree

```         
streamlit (Web UI)
├── tornado (web server)
├── pandas (data manipulation)
├── numpy
├── pillow (image handling)
└── altair (charting, not used in project)

plotly (charts)
└── pandas

tinydb (JSON DB)
└── [no dependencies]

pydantic (validation)
└── [no dependencies]
```

### 8.3 Critical Path Dependencies

**For API to Start:** 1. Python 3.10+ 2. FastAPI + uvicorn 3. SQLAlchemy + asyncpg 4. PostgreSQL 15+ running 5. Environment variables set (`.env` file)

**For PDF Processing:** 6. PyMuPDF (fitz) 7. sentence-transformers + torch 8. OpenAI API key 9. psycopg2 + pgvector (for similarity search) 10. Embeddings populated in database

**For Web UI:** 11. Streamlit 12. Plotly 13. API running at <http://localhost:8000>

------------------------------------------------------------------------

## 9. Security Considerations

### 9.1 Dependency Vulnerabilities

**Automated Scanning:**

``` bash
pip install safety
safety check -r requirements.txt
```

**Known Issues:** - PyMuPDF uses AGPL-3.0 license (implications for commercial use) - python-jose has known JWT vulnerabilities (mitigated by using `cryptography` backend)

**Recommendations:** - Keep dependencies updated: `pip list --outdated` - Monitor CVE databases for critical vulnerabilities - Use Dependabot or Snyk for automated alerts

### 9.2 Secrets Management

**Never commit to Git:** - `.env` file (add to `.gitignore`) - OpenAI API keys - Database passwords - JWT secret keys

**Environment Variables:**

``` bash
# .env (DO NOT COMMIT)
DATABASE_URL=postgresql+asyncpg://user:password@host/db
OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=<32+ character random string>
```

**Generate Secure JWT Key:**

``` bash
openssl rand -hex 32
```

### 9.3 Dependency Pinning

**Current State:** - Backend: Pinned to specific versions (e.g., `fastapi==0.104.1`) - Frontend: Pinned in `cmca_app_2/requirements.txt`

**Rationale:** - Prevents breaking changes from automatic updates - Ensures reproducible builds

**Update Strategy:** - Review changelogs before updating - Test in development environment first - Update one dependency at a time

------------------------------------------------------------------------

## 10. Troubleshooting

### 10.1 Installation Issues

**Issue: `pip install` fails for PyMuPDF on Windows**

**Solution:**

``` bash
# Install Microsoft Visual C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
pip install --upgrade pip wheel setuptools
pip install pymupdf
```

**Issue: `asyncpg` fails to install on macOS**

**Solution:**

``` bash
# Install PostgreSQL development headers
brew install postgresql@15
export PATH="/usr/local/opt/postgresql@15/bin:$PATH"
pip install asyncpg
```

**Issue: `sentence-transformers` model download fails**

**Solution:**

``` bash
# Manually download model
cd ~/.cache/huggingface
git lfs install
git clone https://huggingface.co/intfloat/e5-base-v2
```

### 10.2 Runtime Issues

**Issue: `ModuleNotFoundError: No module named 'app'`**

**Solution:**

``` bash
# Ensure you're in src/backend directory
cd src/backend
uvicorn app.main:app --reload
```

**Issue: `ImportError: cannot import name 'vector' from 'pgvector'`**

**Solution:**

``` sql
-- pgvector extension not enabled
psql -d cmca_audit -c "CREATE EXTENSION vector;"
```

**Issue: `openai.RateLimitError` on every request**

**Solution:** - Check API key validity at <https://platform.openai.com/api-keys> - Verify account has available quota - System will fallback to GPT-3.5-turbo automatically

**Issue: `sentence-transformers` uses CPU instead of GPU**

**Solution:**

``` bash
# Install CUDA-enabled PyTorch
pip uninstall torch
pip install torch==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118

# Verify GPU available
python -c "import torch; print(torch.cuda.is_available())"
```

### 10.3 Database Issues

**Issue: `connection refused` when connecting to PostgreSQL**

**Solution:**

``` bash
# Check if PostgreSQL is running
# Windows:
pg_ctl status

# macOS:
brew services list | grep postgresql

# Linux:
sudo systemctl status postgresql
```

**Issue: `relation "sentence_embeddings" does not exist`**

**Solution:**

``` bash
# Run schema.sql
psql -d cmca_audit -f Database/schema.sql
```

**Issue: `operator does not exist: vector <=> vector`**

**Solution:**

``` bash
# pgvector extension not installed or enabled
psql -d cmca_audit -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 10.4 Performance Issues

**Issue: Embedding model loads slowly (30+ seconds)**

**Solution:** - First load downloads model (\~700 MB), subsequent loads are fast (\<5s) - Use SSD for model cache directory -- Consider preloading model during installation or first run

**Issue: PDF processing takes \>60 seconds**

**Solution:** - Check OpenAI API latency (5-15s per sentence is normal) - Reduce `top_k` parameter in `llm_service.py:46` from 7 to 5 - Increase similarity threshold from 0.70 to 0.75 to reduce LLM calls

**Issue: Database queries slow with 1000+ PDFs**

**Solution:**

``` sql
-- Add indexes if not present
CREATE INDEX IF NOT EXISTS ix_pdfs_project_id ON pdfs (project_id);
CREATE INDEX IF NOT EXISTS ix_pdfs_uploaded_by ON pdfs (uploaded_by);
CREATE INDEX IF NOT EXISTS ix_pdfs_doi ON pdfs (doi);

-- Analyze tables
ANALYZE pdfs;
ANALYZE sentence_embeddings;
```

------------------------------------------------------------------------

**Last Review:** October 14, 2025
