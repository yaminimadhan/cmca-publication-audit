# PostgreSQL Vector Database 

This repository contains a minimal PostgreSQL + pgvector database setup for the CMCA Publication Audit capstone project. It does not generate embeddings - it expects precomputed embeddings provided by an upstream service (your embeddings/gold-standard team).

##  Documentation Overview

This project includes streamlined documentation focused on practical usage:

### Core Documentation Files

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **README.md** | Project overview, quick start, and API reference | First stop for understanding the project |
| **QUICK_REFERENCE.txt** | Command reference for daily operations | When you need quick command reminders |

**For New Users:**
1. Start with **README.md** for project overview and setup
2. Use **QUICK_REFERENCE.txt** for daily operations

** For Daily Use:**
- **QUICK_REFERENCE.txt** - Command cheat sheet
- **README.md** - API reference and examples

**For Team Integration:**
- **README.md** - API documentation for embedding teams

## Scope (your job)
- Stand up a persistent PostgreSQL database with pgvector extension
- Manage collections (tables) and items
- Store documents, metadata, and precomputed embeddings
- Provide a small REST API to add/search items (vector-only)

## Out of scope (handled by embeddings team)
- Generating embeddings (e.g., all-MiniLM-L6-v2)
- Preparing/curating gold standard documents
- Chunking, cleaning, or preprocessing text

## What the embeddings team must provide
- A collection name to write to (string)
- IDs (List[str]) for each item
- Optional documents (List[str])
- Optional metadatas (List[Dict[str, Any]])
- Embeddings (List[List[float]]) of equal length per item
- For search: query_embeddings (List[List[float]]) of same dimension as stored vectors

## Prerequisites
- PostgreSQL 12+ with pgvector extension installed
- Python 3.8+

## Setup PostgreSQL + pgvector
1. Install PostgreSQL (if not already installed)
2. Install pgvector extension:
   ```sql
   CREATE EXTENSION vector;
   ```
3. Use your existing PostgreSQL database (no need to create a new one)

## Environment Variables
Set your database connection:
```bash
export DATABASE_URL="postgresql://postgres:password@localhost:5432/postgres"
```

## .gitignore (recommended)
```
__pycache__/
*.pyc
.venv/
.vscode/
.idea/
.DS_Store
.cache/
.pytest_cache/
.env
```

##  Project Structure

### Core Implementation Files
```
├── pgvector_db.py             # Core database operations (PostgreSQL + pgvector)
├── pgvector_api.py            # FastAPI server for REST endpoints
├── requirements.txt           # Python dependencies
└── VectorDB.code-workspace    # VS Code workspace configuration
```

### Documentation Files
```
├── README.md                  # Project overview and quick start
└── QUICK_REFERENCE.txt        # Command reference for daily use
```

### Data and Output Directories
```
├── data/           # Data storage (raw PDFs, processed data, examples)
├── gold_standard/   # Gold standard documents and codebooks
├── outputs/         # Generated reports and logs
├── proposal/        # Project proposal documents
└── src/            # Source code modules (extraction, ingestion, etc.)
```

## Install
```bash
pip install -r requirements.txt
```

## Run the API
```bash
python pgvector_api.py
# API: http://localhost:8000
```

## API
- POST /collections
  - body: { "collection_name": string, "metadata"?: object }
- GET /collections
- DELETE /collections/{collection_name}
- GET /collections/{collection_name}/count
- POST /items
  - body: {
      "collection_name": string,
      "ids": string[],
      "documents"?: string[],
      "metadatas"?: object[],
      "embeddings"?: number[][]  // REQUIRED when DB should store vectors
    }
- POST /search/vector
  - body: {
      "collection_name": string,
      "query_embeddings": number[][],
      "n_results"?: number,
      "where"?: object
    }

## Example: add items with embeddings
```bash
curl -X POST http://localhost:8000/collections \
  -H "Content-Type: application/json" \
  -d '{"collection_name": "my_docs"}'

curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_docs",
    "ids": ["a", "b"],
    "documents": ["Doc A", "Doc B"],
    "metadatas": [{"tag": "A"}, {"tag": "B"}],
    "embeddings": [[0.1, 0.2, 0.3], [0.2, 0.1, 0.4]]
  }'

curl -X POST http://localhost:8000/search/vector \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_docs",
    "query_embeddings": [[0.1, 0.2, 0.25]],
    "n_results": 2
  }'
```

## Minimal Python usage
```python
from pgvector_db import VectorDB

vdb = VectorDB()
vdb.create_collection("my_docs")

vdb.add_with_embeddings(
	name="my_docs",
	ids=["1"],
	documents=["hello world"],
	metadatas=[{"source": "unit"}],
	embeddings=[[0.1, 0.2, 0.3]],
)

results = vdb.query_by_vector(
	name="my_docs",
	query_embeddings=[[0.1, 0.2, 0.25]],
	n_results=1,
)
print(results)
```

## Recent Updates

**Workspace Cleanup (Latest)**
- Streamlined documentation to focus on essential files
- Kept core functionality: `pgvector_api.py`, `pgvector_db.py`, `README.md`, `QUICK_REFERENCE.txt`

## Deliverables checklist 
- PostgreSQL + pgvector persistent storage works and survives restarts
- Can create/list/delete collections (tables)
- Can add items with ids/documents/metadatas/embeddings
- Can run vector search and return ids/documents/metadatas/distances
- Clear contract documented for upstream embeddings team inputs
- Database connection configurable via environment variables
