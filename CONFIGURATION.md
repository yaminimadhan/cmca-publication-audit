# PostgreSQL + pgvector Configuration Guide

## Quick Setup

### 1. Install PostgreSQL + pgvector
- Install PostgreSQL 12+ on your system
- Install pgvector extension (see installation guide below)

### 2. Set Environment Variable
```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/postgres"

# Windows CMD
set DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres

# Linux/Mac
export DATABASE_URL="postgresql://postgres:password@localhost:5432/postgres"
```

### 3. Run Test Script
```bash
python test_pgvector.py
```

### 4. Test Everything Works
```bash
python test_pgvector.py
```

### 5. Start the API
```bash
python pgvector_api.py
```

## pgvector Installation

### Windows
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Install pgvector:
   ```sql
   CREATE EXTENSION vector;
   ```

### macOS (with Homebrew)
```bash
brew install postgresql
brew install pgvector
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo apt install postgresql-14-pgvector  # adjust version as needed
```

## Connection Examples

### Local Development
```
postgresql://postgres:password@localhost:5432/postgres
```

### With Custom Credentials
```
postgresql://username:password@localhost:5432/database_name
```

### Remote Server
```
postgresql://username:password@your-server.com:5432/database_name
```

## Troubleshooting

### Common Issues
1. **Connection refused**: PostgreSQL not running
2. **Authentication failed**: Wrong username/password
3. **Database does not exist**: Create database first
4. **Extension not found**: Install pgvector extension

### Useful Commands
```sql
-- Check if pgvector is installed
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- Create database
-- Use existing database (no need to create new one)
-- Database: postgres (already exists)

-- Create extension
CREATE EXTENSION vector;

-- List all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```
