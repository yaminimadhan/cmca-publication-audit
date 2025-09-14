from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
from pgvector_db import VectorDB

"""
DB-only PostgreSQL + Arrays API
- Accepts precomputed embeddings (vectors) from an upstream embeddings pipeline
- Does not generate embeddings
- Uses PostgreSQL with arrays for vector storage and similarity search
- Endpoints kept minimal for clarity; extend at the API layer if you need auth, delete-by-ids, etc.
"""

app = FastAPI(
    title="PostgreSQL Vector Database API (DB-only)",
    description="REST API for PostgreSQL + Arrays that accepts precomputed embeddings",
    version="3.2.0"
)

# Initialize PostgreSQL connection (configure via DATABASE_URL environment variable)
db = VectorDB()

# ------------------------------------
# Models (request bodies)
# ------------------------------------
class CollectionRequest(BaseModel):
    collection_name: str
    metadata: Optional[Dict[str, Any]] = None  # optional tags/owners/version

class AddItemsRequest(BaseModel):
    collection_name: str
    ids: List[str]  # upstream must guarantee uniqueness or define update policy
    documents: Optional[List[str]] = None  # optional raw text for debugging/audits
    metadatas: Optional[List[Dict[str, Any]]] = None  # optional JSON metadata per item
    embeddings: Optional[List[List[float]]] = None  # REQUIRED when storing vectors

class VectorSearchRequest(BaseModel):
    collection_name: str
    query_embeddings: List[List[float]]  # vectors of same dimension as stored items
    n_results: int = 5
    where: Optional[Dict[str, Any]] = None  # optional filter (e.g., {"version": "v1"})

# ------------------------------------
# Health / Root
# ------------------------------------
@app.get("/")
async def root():
    return {"message": "DB-only PostgreSQL + pgvector API", "version": "3.2.0"}

# ------------------------------------
# Collections
# ------------------------------------
@app.get("/collections")
async def list_collections():
    try:
        return {"collections": db.list_collections()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/collections")
async def create_collection(req: CollectionRequest):
    """
    Create (or get) a collection.
    - Use metadata to store descriptive info (e.g., version, owner)
    - Enforce ACLs/validation at a higher layer if needed
    """
    try:
        db.create_collection(req.collection_name, req.metadata)
        return {"message": f"Collection '{req.collection_name}' ready"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """
    Delete a collection.
    WARNING: irreversible. Add soft-delete policies at higher layers if required.
    """
    try:
        db.delete_collection(collection_name)
        return {"message": f"Collection '{collection_name}' deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections/{collection_name}/count")
async def count(collection_name: str):
    """Return number of items in a collection (useful for health/observability)."""
    try:
        return {"count": db.count(collection_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------
# Items (insert vectors)
# ------------------------------------
@app.post("/items")
async def add_items(req: AddItemsRequest):
    """
    Insert items into a collection.
    Expectations:
    - Upstream ensures len(ids) == len(embeddings) (and documents/metadatas if provided)
    - Embedding dimension must be consistent across inserts/queries
    - Define de-duplication/update policy at a higher layer if needed
    """
    try:
        if req.documents is None and req.embeddings is None:
            raise HTTPException(status_code=400, detail="Provide documents or embeddings")
        db.add_with_embeddings(
            name=req.collection_name,
            documents=req.documents,
            embeddings=req.embeddings,
            metadatas=req.metadatas,
            ids=req.ids,
        )
        return {"message": f"Added {len(req.ids)} items"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------
# Vector search
# ------------------------------------
@app.post("/search/vector")
async def search_by_vector(req: VectorSearchRequest):
    """
    Vector similarity search.
    - Apply 'where' filters for versioning/source/category semantics
    - Add post-filtering or thresholding at higher layers if needed
    """
    try:
        results = db.query_by_vector(
            name=req.collection_name,
            query_embeddings=req.query_embeddings,
            n_results=req.n_results,
            where=req.where,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------
# Health
# ------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

# Entry point for local runs
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
