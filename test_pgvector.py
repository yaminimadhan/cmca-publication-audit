#!/usr/bin/env python3
"""
Test script for PostgreSQL vector database functionality
"""

import os
import psycopg2
import json
import math

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    
    return dot_product / (magnitude_a * magnitude_b)

def test_basic_functionality():
    """Test basic database operations"""
    print("🧪 Testing PostgreSQL Vector Database Functionality")
    print("=" * 50)
    
    # Initialize database connection
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Test collection operations
    collection_name = "test_collection"
    
    try:
        with conn.cursor() as cur:
            # Create collection
            cur.execute("""
                INSERT INTO vector_collections (collection_name) 
                VALUES (%s) 
                ON CONFLICT (collection_name) DO NOTHING;
            """, (collection_name,))
            print(f"✅ Created collection: {collection_name}")
            
            # List collections
            cur.execute("SELECT collection_name FROM vector_collections;")
            collections = [row[0] for row in cur.fetchall()]
            print(f"✅ Collections: {collections}")
            
            # Add test data
            test_data = [
                ("test_1", collection_name, "This is a test document", json.dumps({"source": "test"}), [0.1, 0.2, 0.3, 0.4]),
                ("test_2", collection_name, "Another test document", json.dumps({"source": "test"}), [0.2, 0.1, 0.4, 0.3])
            ]
            
            for data in test_data:
                cur.execute("""
                    INSERT INTO vector_documents (id, collection_name, document, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        document = EXCLUDED.document,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                """, data)
            
            print("✅ Added test data")
            
            # Check count
            cur.execute("SELECT COUNT(*) FROM vector_documents WHERE collection_name = %s;", (collection_name,))
            count = cur.fetchone()[0]
            print(f"✅ Collection count: {count}")
            
            # Test vector search (using cosine similarity)
            query_embedding = [0.1, 0.2, 0.25, 0.35]
            
            cur.execute("""
                SELECT id, document, metadata, embedding
                FROM vector_documents
                WHERE collection_name = %s;
            """, (collection_name,))
            
            results = cur.fetchall()
            
            # Calculate similarities
            similarities = []
            for doc_id, document, metadata, embedding in results:
                similarity = cosine_similarity(query_embedding, embedding)
                similarities.append((doc_id, document, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[2], reverse=True)
            
            print("✅ Vector search results:")
            for i, (doc_id, document, similarity) in enumerate(similarities[:2]):
                print(f"   Result {i+1}: {similarity:.3f} - {document}")
            
            # Clean up
            cur.execute("DELETE FROM vector_documents WHERE collection_name = %s;", (collection_name,))
            cur.execute("DELETE FROM vector_collections WHERE collection_name = %s;", (collection_name,))
            print("✅ Cleaned up test collection")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        conn.close()
        return False

def main():
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL environment variable not set!")
        print("Please set DATABASE_URL environment variable and ensure PostgreSQL is running")
        return
    
    success = test_basic_functionality()
    
    if success:
        print("\n🎉 All tests passed! Your PostgreSQL vector database is working correctly.")
    else:
        print("\n❌ Tests failed. Please check your setup.")

if __name__ == "__main__":
    main()
