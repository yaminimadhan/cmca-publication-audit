import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import json
import os
import math

"""
VectorDB: Minimal wrapper around PostgreSQL with array-based vector storage and search.
- This module does NOT create embeddings. Upstream services must provide embeddings.
- Uses PostgreSQL arrays for vector storage (no pgvector extension required).
- Safe integration points are documented as comments below.
"""

class VectorDB:
	"""Minimal PostgreSQL wrapper with array-based vector storage that expects precomputed embeddings.
	
	Responsibilities
	- Initialize connection to PostgreSQL with array-based vector storage
	- Create/list/delete collections (tables)
	- Add items with provided embeddings and optional documents/metadata
	- Query collections using vector similarity search (cosine similarity)
	
	Integration notes
	- If you need auth, wrap calls at the API layer before invoking this class
	- If you need data validation/normalization, perform it before calling add/query
	- Database connection details should be configured via environment variables
	"""
	def __init__(self, connection_string: str = None) -> None:
		# Use environment variables for connection if not provided
		if connection_string is None:
			connection_string = os.getenv(
				'DATABASE_URL', 
				'postgresql://postgres:password@localhost:5432/postgres'
			)
		
		self.connection_string = connection_string
		self._ensure_extension()

	def _ensure_extension(self):
		"""Ensure database is ready (no pgvector extension needed for our implementation)."""
		with psycopg2.connect(self.connection_string) as conn:
			with conn.cursor() as cur:
				# Set search path to capstone_vector schema
				cur.execute("SET search_path TO capstone_vector, public")
				# No extension needed - we use PostgreSQL arrays
				conn.commit()

	def _get_connection(self):
		"""Get a database connection."""
		conn = psycopg2.connect(self.connection_string)
		# Set search path to capstone_vector schema
		with conn.cursor() as cur:
			cur.execute("SET search_path TO capstone_vector, public")
		return conn
	
	def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
		"""Calculate cosine similarity between two vectors."""
		dot_product = sum(x * y for x, y in zip(a, b))
		magnitude_a = math.sqrt(sum(x * x for x in a))
		magnitude_b = math.sqrt(sum(x * x for x in b))
		
		if magnitude_a == 0 or magnitude_b == 0:
			return 0
		
		return dot_product / (magnitude_a * magnitude_b)

	def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None):
		"""Create or get a collection (table).
		
		Placeholders / extension points
		- Attach collection-level metadata for versioning, owners, tags, etc.
		- Enforce naming conventions or ACLs at the API layer before calling this.
		"""
		with self._get_connection() as conn:
			with conn.cursor() as cur:
				# Create table if it doesn't exist
				cur.execute(f"""
					CREATE TABLE IF NOT EXISTS {name} (
						id TEXT PRIMARY KEY,
						document TEXT,
						metadata JSONB,
						embedding REAL[]  -- Vector stored as PostgreSQL array
					)
				""")
				conn.commit()
		return name

	def delete_collection(self, name: str) -> None:
		"""Delete a collection (table).
		
		Warning
		- This is irreversible. Consider soft-delete policies at the API layer.
		"""
		with self._get_connection() as conn:
			with conn.cursor() as cur:
				cur.execute(f"DROP TABLE IF EXISTS {name}")
				conn.commit()

	def list_collections(self) -> List[str]:
		"""List collection names (table names) for observability or UI pick-lists."""
		with self._get_connection() as conn:
			with conn.cursor() as cur:
				cur.execute("""
					SELECT table_name 
					FROM information_schema.tables 
					WHERE table_schema = 'capstone_vector' 
					AND table_name NOT LIKE 'pg_%'
				""")
				return [row[0] for row in cur.fetchall()]

	def count(self, name: str) -> int:
		"""Return item count in a collection (useful for health and monitoring)."""
		with self._get_connection() as conn:
			with conn.cursor() as cur:
				cur.execute(f"SELECT COUNT(*) FROM {name}")
				return cur.fetchone()[0]

	def add_with_embeddings(
		self,
		name: str,
		documents: Optional[List[str]] = None,
		embeddings: Optional[List[List[float]]] = None,
		metadatas: Optional[List[Dict[str, Any]]] = None,
		ids: Optional[List[str]] = None,
	) -> None:
		"""
		Add items to a collection. One of documents or embeddings must be provided.
		If embeddings are provided, they are stored directly (no embedding_function used).
		
		Expectations
		- Upstream must ensure ids/embeddings/documents/metadatas have matching lengths
		- Upstream must ensure embedding dimension is consistent across inserts and queries
		- Upstream should deduplicate ids or choose an update policy at the API level
		"""
		if not ids:
			raise ValueError("ids are required")
		
		with self._get_connection() as conn:
			with conn.cursor() as cur:
				# Prepare data for batch insert
				data = []
				for i, item_id in enumerate(ids):
					doc = documents[i] if documents and i < len(documents) else None
					meta = json.dumps(metadatas[i]) if metadatas and i < len(metadatas) else None
					embedding = embeddings[i] if embeddings and i < len(embeddings) else None
					
					data.append((item_id, doc, meta, embedding))
				
				# Batch insert with ON CONFLICT for upsert behavior
				cur.executemany(f"""
					INSERT INTO {name} (id, document, metadata, embedding)
					VALUES (%s, %s, %s, %s)
					ON CONFLICT (id) DO UPDATE SET
						document = EXCLUDED.document,
						metadata = EXCLUDED.metadata,
						embedding = EXCLUDED.embedding
				""", data)
				conn.commit()

	def query_by_vector(
		self,
		name: str,
		query_embeddings: List[List[float]],
		n_results: int = 5,
		where: Optional[Dict[str, Any]] = None,
	) -> Dict[str, Any]:
		"""
		Vector similarity search using cosine distance.
		
		Integration notes
		- Apply business filters via the 'where' clause (e.g., version, source)
		- Post-process results (reranking/thresholding) at the API layer if required
		"""
		if not query_embeddings:
			return {"ids": [], "documents": [], "metadatas": [], "distances": []}
		
		query_vector = query_embeddings[0]
		
		with self._get_connection() as conn:
			with conn.cursor(cursor_factory=RealDictCursor) as cur:
				# Build WHERE clause for metadata filtering
				where_clause = ""
				params = [query_vector, n_results]
				
				if where:
					where_conditions = []
					for key, value in where.items():
						if isinstance(value, str):
							where_conditions.append(f"metadata->>'{key}' = %s")
							params.append(value)
						else:
							where_conditions.append(f"metadata->>'{key}' = %s")
							params.append(str(value))
					
					if where_conditions:
						where_clause = "WHERE " + " AND ".join(where_conditions)
				
				# Get all documents and calculate similarities
				cur.execute(f"""
					SELECT id, document, metadata, embedding
					FROM {name}
					{where_clause}
				""", params)
				
				results = cur.fetchall()
				
				# Calculate cosine similarities
				similarities = []
				for row in results:
					similarity = self._cosine_similarity(query_vector, row['embedding'])
					similarities.append((row['id'], row['document'], row['metadata'], similarity))
				
				# Sort by similarity (descending) and take top n_results
				similarities.sort(key=lambda x: x[3], reverse=True)
				top_results = similarities[:n_results]
				
				# Format results to match Chroma API format
				return {
					"ids": [[row[0] for row in top_results]],
					"documents": [[row[1] for row in top_results]],
					"metadatas": [[json.loads(row[2]) if row[2] else {} for row in top_results]],
					"distances": [[1 - row[3] for row in top_results]]  # Convert similarity to distance
				}

	def query_by_text(
		self,
		name: str,
		query_texts: List[str],
		n_results: int = 5,
		where: Optional[Dict[str, Any]] = None,
	) -> Dict[str, Any]:
		"""
		Text query - not supported in this implementation.
		This method is kept for API compatibility but will raise an error.
		
		Note: Use query_by_vector with precomputed embeddings instead.
		"""
		raise NotImplementedError("Text queries not supported. Use query_by_vector with precomputed embeddings.")
