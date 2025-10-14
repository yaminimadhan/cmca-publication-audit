# Installation Guide
# CMCA Publication Audit System

**This is the authoritative installation guide with comprehensive step-by-step instructions.**

**Duration:** 30 minutes for complete installation from scratch  
**Alternative:** For experienced users, see [QUICKSTART.md](QUICKSTART.md) (10-minute rapid setup)

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.10 or 3.11 installed
- [ ] PostgreSQL 15 or later installed
- [ ] OpenAI API key obtained
- [ ] 20 GB free disk space
- [ ] Internet connection (for downloading models)
- [ ] Administrator/sudo access (for PostgreSQL)

---

## Installation Steps

### Step 1: Install System Prerequisites

#### Python 3.10+

**Windows:**
```powershell
# Download from https://www.python.org/downloads/
# OR use winget:
winget install Python.Python.3.11

# Verify:
python --version
```

**macOS:**
```bash
brew install python@3.11

# Verify:
python3.11 --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Verify:
python3.11 --version
```

#### PostgreSQL 15+

**Windows:**
```powershell
# Download from https://www.postgresql.org/download/windows/
# OR use Chocolatey:
choco install postgresql15 --params '/Password:YourPassword'

# Verify:
psql --version
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15

# Verify:
psql --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install postgresql-15 postgresql-contrib-15
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify:
psql --version
```

#### pgvector Extension

**macOS:**
```bash
brew install pgvector
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install postgresql-15-pgvector
```

**Windows/Other:**
```bash
# Install from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

---

### Step 2: Clone Repository

```bash
git clone <repository-url>
cd cmca-publication-audit-main
```

---

### Step 3: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# Verify activation (should show .venv in prompt)
which python  # macOS/Linux
where python  # Windows
```

---

### Step 4: Install Python Dependencies

#### Backend Dependencies

```bash
cd src/backend
pip install --upgrade pip
pip install -r requirements.txt

# This will install ~50 packages, may take 5-10 minutes
# Large downloads: torch (~800 MB), transformers (~400 MB)
```

**Verify Installation:**
```bash
python -c "import fastapi; print(f'✓ FastAPI {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'✓ SQLAlchemy {sqlalchemy.__version__}')"
python -c "import fitz; print(f'✓ PyMuPDF {fitz.__version__}')"
python -c "from sentence_transformers import SentenceTransformer; print('✓ sentence-transformers')"
python -c "import openai; print(f'✓ OpenAI {openai.__version__}')"
```

#### Frontend Dependencies

```bash
cd ../../cmca_app_2
pip install -r requirements.txt
```

**Verify Installation:**
```bash
python -c "import streamlit; print(f'✓ Streamlit {streamlit.__version__}')"
python -c "import plotly; print(f'✓ Plotly {plotly.__version__}')"
```

---

### Step 5: Download Embedding Model

This downloads ~700 MB on first run:

```bash
cd ..
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('intfloat/e5-base-v2'); print('✓ Model downloaded to ~/.cache/huggingface/')"
```

**Model Cache Location:**
- **Linux/macOS:** `~/.cache/huggingface/hub/models--intfloat--e5-base-v2/`
- **Windows:** `C:\Users\{Username}\.cache\huggingface\hub\models--intfloat--e5-base-v2\`

---

### Step 6: Setup Database

#### Create Database

```bash
# Linux/macOS:
sudo -u postgres createdb cmca_audit

# Windows (as postgres user):
createdb cmca_audit
```

#### Run Schema

```bash
cd Database
psql -d cmca_audit -f schema.sql

# Verify tables created:
psql -d cmca_audit -c "\dt"
# Should show: users, projects, pdfs, sentence_embeddings, etc.
```

#### Enable pgvector Extension

```bash
psql -d cmca_audit -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify:
psql -d cmca_audit -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
# Should return 1 row
```

---

### Step 7: Populate Gold Standard Embeddings

```bash
cd ../src

# IMPORTANT: Edit store_embedding.py lines 11-16 with your DB credentials
# Open in editor and change:
#   password="YOUR_PASSWORD"  # Replace with your PostgreSQL password

nano store_embedding.py  # or use your preferred editor

# Run embedding script:
python store_embedding.py
```

**Expected Output:**
```
Loading embedding model.
Loading sentences from ../docs/gold_standard/goldstandard.txt
Connecting to PostgreSQL
Inserting 44 embeddings into database...
All embeddings inserted successfully.
```

**Verify Embeddings:**
```bash
psql -d cmca_audit -c "SELECT COUNT(*) FROM sentence_embeddings;"
# Should return 44 (or number of phrases in goldstandard.txt)
```

---

### Step 8: Configure Environment Variables

```bash
cd ..

# Copy template:
cp env.template .env

# Edit .env file with your values:
nano .env  # or use your preferred editor
```

**Minimum Required Configuration:**

```bash
# .env file
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/cmca_audit
OPENAI_API_KEY=sk-your-actual-api-key-here
JWT_SECRET_KEY=$(openssl rand -hex 32)  # Generate random key
UPLOAD_DIR=storage/pdfs
```

**Generate Secure JWT Key:**
```bash
# Linux/macOS:
openssl rand -hex 32

# Windows (PowerShell):
-join ((1..32) | ForEach-Object {'{0:x2}' -f (Get-Random -Maximum 256)})
```

**Create Upload Directory:**
```bash
mkdir -p storage/pdfs
```

---

### Step 9: Update Database Credentials in Scripts

**IMPORTANT:** Two scripts have hardcoded database credentials that need updating:

#### File 1: `src/backend/app/services/similarity_search.py` (lines 11-16)

```python
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="cmca_audit",
    user="postgres",
    password="YOUR_PASSWORD"  # <-- UPDATE THIS
)
```

#### File 2: `src/store_embedding.py` (lines 21-26)

```python
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="cmca_audit",
    user="postgres",
    password="YOUR_PASSWORD"  # <-- UPDATE THIS
)
```

**TODO (Future):** Migrate these to use environment variables.

---

### Step 10: Start Services

#### Terminal 1: Start API Server

```bash
cd src/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test API:**
```bash
# In another terminal:
curl http://localhost:8000/health
# Should return: {"ok":true}

curl http://localhost:8000/health/db
# Should return: {"db":"ok"}
```

**API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Terminal 2: Start Web UI

```bash
cd cmca_app_2
streamlit run app.py
```

**Expected Output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Browser should automatically open to http://localhost:8501

---

### Step 11: Create First User and Test

#### Register User via API

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "user_type": "admin"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Test Web UI Login

1. Open http://localhost:8501
2. Enter username: `admin`
3. Enter password: `admin123`
4. Click "Sign In"
5. Should redirect to dashboard

#### Create Test Project

1. In dashboard, expand "🗂️ Create New Project"
2. Enter project name: "Test Project"
3. Click "Create Project"
4. Project should appear in dropdown

#### Upload Test PDF

1. Expand "📤 Upload New PDF"
2. Click "Browse files" and select a scientific PDF
3. Select "Test Project" from dropdown
4. Click "Upload"
5. Wait 10-30 seconds for processing
6. PDF card should appear in dashboard with CMCA result (✅ or ❌)

---

## Post-Installation

### Verify Installation Checklist

- [ ] API health check returns `{"ok": true}`
- [ ] Database health check returns `{"db": "ok"}`
- [ ] Swagger UI loads at http://localhost:8000/docs
- [ ] Web UI loads at http://localhost:8501
- [ ] User registration and login successful
- [ ] Project creation successful
- [ ] PDF upload and processing successful (10-30 seconds)
- [ ] PDF detail page shows metadata and CMCA result
- [ ] Highlighted PDF downloadable

### Common Issues and Solutions

#### API won't start: "ModuleNotFoundError: No module named 'app'"

**Solution:** Ensure you're in `src/backend` directory when running uvicorn.

#### Database connection error: "connection refused"

**Solution:** Check PostgreSQL is running:
```bash
# macOS:
brew services list | grep postgresql

# Linux:
sudo systemctl status postgresql

# Windows:
pg_ctl status
```

#### pgvector error: "extension 'vector' does not exist"

**Solution:**
```bash
psql -d cmca_audit -c "CREATE EXTENSION vector;"
```

#### OpenAI API error: "Invalid API key"

**Solution:** Verify your API key at https://platform.openai.com/api-keys and update `.env` file.

#### Embedding model download fails

**Solution:**
```bash
# Check internet connection, then retry:
rm -rf ~/.cache/huggingface/hub/models--intfloat--e5-base-v2/
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/e5-base-v2')"
```

---

## Uninstallation

### Remove Python Virtual Environment

```bash
# Deactivate virtual environment
deactivate

# Delete virtual environment directory
rm -rf .venv
```

### Remove Database

```bash
dropdb cmca_audit
```

### Remove Model Cache

```bash
rm -rf ~/.cache/huggingface/hub/models--intfloat--e5-base-v2/
```

---

## Next Steps

### Usage and Documentation
- **Usage examples:** [QUICKSTART.md](QUICKSTART.md) - Learn how to use the system
- **System architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) - Understand system design
- **Dependency reference:** [SOFTWARE_DEPENDENCIES.md](SOFTWARE_DEPENDENCIES.md) - Complete dependency specification
- **Requirements:** [REQUIREMENTS.md](REQUIREMENTS.md) - Full system requirements

### Additional Resources
- **Environment template:** [env.template](env.template) - Configuration reference
- **Documentation guide:** [README.md - Documentation Guide](README.md#documentation-guide) - All documentation

---

## Getting Help

**Installation Support:**
- **Common issues:** See "Common Issues and Solutions" section above
- **Dependency conflicts:** [SOFTWARE_DEPENDENCIES.md - Section 10](SOFTWARE_DEPENDENCIES.md#10-troubleshooting)
- **General troubleshooting:** [README.md - Troubleshooting](README.md#troubleshooting)
- **Review logs:** Check terminal output for specific error messages
- **Verify prerequisites:** Ensure all prerequisites installed correctly

---

**Last Updated:** October 14, 2025

