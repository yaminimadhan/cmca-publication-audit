from sentence_transformers import SentenceTransformer
import psycopg2
from pathlib import Path

#Path
TEXT_FILE = Path("../docs/gold_standard/goldstandard.txt")

#PostgreSQL connection
PG_HOST = "localhost"
PG_DB = "postgres"
PG_USER = "postgres"
PG_PASSWORD = "Capstone"

#Load model
print("Loading embedding model.")
model = SentenceTransformer("intfloat/e5-base-v2")

#Read sentences
print(f"Loading sentences from {TEXT_FILE}")
lines = TEXT_FILE.read_text(encoding="utf-8").splitlines()
sentences = [f"passage: {line.strip()}" for line in lines if line.strip()] #List of sentences in the format that embedding expects.


#Connect to DB
print("Connecting to PostgreSQL")
conn = psycopg2.connect(
    host=PG_HOST,
    dbname=PG_DB,
    user=PG_USER,
    password=PG_PASSWORD or None
)
cur = conn.cursor()


#Inserting
print(f"Inserting {len(sentences)} embeddings into database...")
for sentence in sentences:
    embedding = model.encode(sentence).tolist()
    cur.execute(
        "INSERT INTO sentence_embeddings (sentence, embedding) VALUES (%s, %s)",
        (sentence, embedding)
    )

conn.commit()
cur.close()
conn.close()
print("All embeddings inserted successfully.")
