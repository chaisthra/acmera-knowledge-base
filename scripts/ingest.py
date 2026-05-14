"""
Ingest documents into pgvector.
Run: python scripts/ingest.py
Run with strategy: python scripts/ingest.py --strategy sliding_window
"""
import os
import glob
import json
import argparse
from openai import OpenAI
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "..", "corpus")


def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5433"),
        user=os.getenv("PG_USER", "workshop"),
        password=os.getenv("PG_PASSWORD", "workshop123"),
        dbname=os.getenv("PG_DATABASE", "acmera_kb"),
    )
    register_vector(conn)
    return conn


def embed_texts(texts):
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]


def ingest(strategy="fixed_size"):
    from chunker import get_chunker
    chunk_fn = get_chunker(strategy)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM chunks;")

    doc_files = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md")))
    total_chunks = 0

    for filepath in doc_files:
        doc_name = os.path.basename(filepath)
        with open(filepath, "r") as f:
            content = f.read()

        chunks = chunk_fn(content)
        print(f"  {doc_name}: {len(chunks)} chunks")

        for batch_start in range(0, len(chunks), 20):
            batch = chunks[batch_start:batch_start + 20]
            embeddings = embed_texts(batch)

            for i, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                chunk_index = batch_start + i
                metadata = json.dumps({
                    "doc_name": doc_name,
                    "chunk_index": chunk_index,
                    "strategy": strategy,
                })
                cur.execute(
                    """INSERT INTO chunks (doc_name, chunk_index, content, embedding, metadata)
                       VALUES (%s, %s, %s, %s::vector, %s)""",
                    (doc_name, chunk_index, chunk, embedding, metadata),
                )

        total_chunks += len(chunks)

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone: {len(doc_files)} documents, {total_chunks} chunks  [strategy={strategy}]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="fixed_size",
                        choices=["fixed_size", "sliding_window", "sentence_aware"])
    args = parser.parse_args()
    ingest(strategy=args.strategy)
