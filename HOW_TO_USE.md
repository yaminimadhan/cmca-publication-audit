# PostgreSQL Vector Database - Complete Setup Guide

This guide provides step-by-step instructions for setting up and using the PostgreSQL vector database system.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Database Configuration](#database-configuration)
4. [Testing the Setup](#testing-the-setup)
5. [Using the API](#using-the-api)
6. [Integration Guide](#integration-guide)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

## 🔧 Prerequisites

### Required Software
- **Python 3.8+** - [Download from python.org](https://www.python.org/downloads/)
- **PostgreSQL 17** - Already installed on your system
- **Git** - For version control

### Required Python Packages
All dependencies are listed in `requirements.txt`:
```
psycopg2-binary>=2.9.0
pgvector>=0.2.0
fastapi>=0.100.0
uvicorn>=0.20.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
```

## 🚀 Initial Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Environment Variables
```powershell
# Set the database connection string
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/postgres"
```

### Step 3: Test the Setup
```bash
python test_pgvector.py
```

This will:
- Test database connection
- Create test collections and documents
- Verify vector similarity search works

## 🗄️ Database Configuration

### Database Structure

The system creates two main tables:

#### `vector_collections`
- `collection_name` (TEXT PRIMARY KEY) - Name of the collection
- `created_at` (TIMESTAMP) - When the collection was created

#### `vector_documents`
- `id` (TEXT PRIMARY KEY) - Unique document identifier
- `collection_name` (TEXT) - Reference to collection
- `document` (TEXT) - The actual document content
- `metadata` (JSONB) - Additional metadata
- `embedding` (REAL[]) - Vector embedding as PostgreSQL array
- `created_at` (TIMESTAMP) - When the document was added

### Connection Details
- **Host**: localhost
- **Port**: 5432
- **Database**: postgres
- **Username**: postgres
- **Password**: password

## 🧪 Testing the Setup

### Basic Test
```bash
python test_pgvector.py
```

This will:
- Create a test collection
- Add sample documents with embeddings
- Perform vector similarity search
- Display results

### API Test
```bash
# Start the API server
python pgvector_api.py

# In another terminal, test the API
curl http://localhost:8000/collections
```

## 🌐 Using the API

### Starting the API Server
```bash
python pgvector_api.py
```

The API will be available at: `http://localhost:8000`

### API Endpoints

#### 1. List Collections
```bash
GET /collections
```

#### 2. Create Collection
```bash
POST /collections
Content-Type: application/json

{
    "name": "my_collection"
}
```

#### 3. Add Documents
```bash
POST /items
Content-Type: application/json

{
    "collection_name": "my_collection",
    "ids": ["doc1", "doc2"],
    "documents": ["Document 1 content", "Document 2 content"],
    "metadatas": [{"type": "example"}, {"type": "example"}],
    "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
}
```

#### 4. Vector Search
```bash
POST /search/vector
Content-Type: application/json

{
    "collection_name": "my_collection",
    "query_embedding": [0.1, 0.2, 0.3],
    "n_results": 5
}
```

### Example API Usage (Python)
```python
import requests
import json

# Add documents
data = {
    "collection_name": "test_collection",
    "ids": ["doc1"],
    "documents": ["This is a test document"],
    "metadatas": [{"type": "test"}],
    "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]]
}

response = requests.post("http://localhost:8000/items", json=data)
print(response.json())

# Search
search_data = {
    "collection_name": "test_collection",
    "query_embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
    "n_results": 3
}

response = requests.post("http://localhost:8000/search/vector", json=search_data)
print(response.json())
```

## 🔗 Integration Guide

### For Embedding Generation Team
The vector database expects precomputed embeddings in the following format:

```python
# Expected embedding format
embeddings = [
    [0.1, 0.2, 0.3, 0.4, 0.5],  # Document 1 embedding
    [0.6, 0.7, 0.8, 0.9, 1.0]   # Document 2 embedding
]

# All embeddings must have the same dimension (384 for all-MiniLM-L6-v2)
```

### Integration Points

#### 1. Document Processing Pipeline
```python
# Your embedding generation code should output:
documents_data = {
    "ids": ["doc_1", "doc_2"],
    "documents": ["Document content 1", "Document content 2"],
    "metadatas": [{"source": "file1.txt"}, {"source": "file2.txt"}],
    "embeddings": [[...], [...]]  # Precomputed embeddings
}

# Send to vector database
import requests
response = requests.post("http://localhost:8000/items", json=documents_data)
```

#### 2. Search Integration
```python
# Generate query embedding
query_embedding = your_embedding_model.encode("search query")

# Search vector database
search_data = {
    "collection_name": "your_collection",
    "query_embedding": query_embedding.tolist(),
    "n_results": 10
}

response = requests.post("http://localhost:8000/search/vector", json=search_data)
results = response.json()
```

### Environment Variables
Create a `.env` file for production:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
API_HOST=0.0.0.0
API_PORT=8000
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Connection Failed
```
❌ Connection failed: password authentication failed
```
**Solution**: Check PostgreSQL service is running and credentials are correct:
```bash
# Check if PostgreSQL service is running
# Verify connection string: postgresql://postgres:password@localhost:5432/postgres
```

#### 2. pgvector Extension Not Found
```
❌ pgvector extension not available
```
**Solution**: Use the working setup (no pgvector required):
```bash
python working_setup.py
```

#### 3. Docker Issues
```
❌ Docker daemon not running
```
**Solution**: Start Docker Desktop or use the local PostgreSQL setup

#### 4. Permission Denied
```
❌ Permission denied
```
**Solution**: Run PowerShell as Administrator

### Database Connection Test
```bash
python test_connection.py
```

### Reset Everything
```bash
# Check PostgreSQL service
# Verify connection string
# Test with: python test_pgvector.py

# Test everything
python test_pgvector.py
```

## 📊 Advanced Usage

### Custom Vector Dimensions
The system supports any vector dimension. For `all-MiniLM-L6-v2`, use 384 dimensions:

```python
# Example with 384-dimensional embeddings
embeddings = [
    [0.1] * 384,  # Document 1
    [0.2] * 384   # Document 2
]
```

### Metadata Filtering
```python
# Search with metadata filter
search_data = {
    "collection_name": "my_collection",
    "query_embedding": [0.1, 0.2, 0.3],
    "n_results": 5,
    "where": {"type": "document"}  # Filter by metadata
}
```

### Batch Operations
```python
# Add multiple documents at once
documents_data = {
    "collection_name": "large_collection",
    "ids": [f"doc_{i}" for i in range(1000)],
    "documents": [f"Document {i} content" for i in range(1000)],
    "metadatas": [{"batch": "large_import"} for i in range(1000)],
    "embeddings": [[0.1] * 384 for i in range(1000)]
}
```

### Performance Optimization
1. **Indexing**: The system automatically creates indexes for collections and metadata
2. **Batch Inserts**: Use batch operations for large datasets
3. **Connection Pooling**: The API uses connection pooling for better performance

## 📁 File Structure

```
├── pgvector_db.py          # Core database operations
├── pgvector_api.py         # FastAPI server
├── test_pgvector.py        # Test script
├── requirements.txt        # Python dependencies
├── README.md              # Project overview
├── CONFIGURATION.md       # Configuration guide
├── VECTOR_DB_SUMMARY.txt  # Integration summary
└── HOW_TO_USE.md          # This file
```

## 🎯 Quick Start Checklist

- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Set environment variable: `$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/postgres"`
- [ ] Test setup: `python test_pgvector.py`
- [ ] Start API: `python pgvector_api.py`
- [ ] Test API: `curl http://localhost:8000/collections`

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run the connection test: `python test_connection.py`
3. Check PostgreSQL service status
4. Verify environment variables are set correctly

## 🔄 Updates and Maintenance

### Regular Maintenance
- Monitor database size and performance
- Backup important collections
- Update dependencies regularly

### Scaling Considerations
- For large datasets, consider using pgvector with Docker
- Monitor API performance and add load balancing if needed
- Consider database replication for high availability

---

**Note**: This setup uses PostgreSQL arrays instead of the pgvector extension for maximum compatibility. For production use with large datasets, consider migrating to pgvector for better performance.
