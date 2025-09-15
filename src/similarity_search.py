from sentence_transformers import SentenceTransformer
import psycopg2
from pathlib import Path


#Load model
model = SentenceTransformer("intfloat/e5-base-v2")

#Function to check the similarity
def search_sentences(sentences, k=30):
    #Connect to DB
    conn = psycopg2.connect(
        host="localhost", dbname="postgres", user="postgres", password="Capstone"
    )
    cur = conn.cursor()

    results = {}

    #Batch encode all sentences at once
    embeddings = model.encode(sentences).tolist()

    #Loop over sentence + embedding pairs
    for sent, emb in zip(sentences, embeddings):
        emb_str = "[" + ",".join(map(str, emb)) + "]"
        cur.execute("""
            SELECT sentence, 1 - (embedding <=> %s::vector) AS cosine_similarity
            FROM sentence_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """, (emb_str, emb_str, k))  #k = 30 by default
        results[sent] = cur.fetchall()

    cur.close()
    conn.close()
    return results
