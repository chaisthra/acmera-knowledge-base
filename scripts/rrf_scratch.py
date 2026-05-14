"""
Reciprocal Rank Fusion from scratch — A2.2

Fuses dense (embedding) results with BM25 keyword results.
Score per doc = 1/(k + rank_in_dense) + 1/(k + rank_in_bm25)
Docs only in one list get a penalty rank = length of that list.

Run:
  python scripts/rrf_scratch.py
"""
import os
import sys
import json
import psycopg2
from pgvector.psycopg2 import register_vector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from bm25_scratch import load_all_chunks, bm25_simple

client = OpenAI()


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


def dense_retrieve(query, top_k=10):
    """Standard embedding-based retrieval."""
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    embedding = response.data[0].embedding

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, doc_name, chunk_index, content, metadata,
                  1 - (embedding <=> %s::vector) AS similarity
           FROM chunks ORDER BY embedding <=> %s::vector LIMIT %s""",
        (embedding, embedding, top_k),
    )
    results = []
    for row in cur.fetchall():
        results.append({
            "id": row[0], "doc_name": row[1], "chunk_index": row[2],
            "content": row[3],
            "metadata": row[4] if isinstance(row[4], dict) else json.loads(row[4]),
            "similarity": round(float(row[5]), 4),
        })
    cur.close()
    conn.close()
    return results


def reciprocal_rank_fusion(dense, bm25, k=60):
    """
    RRF fusion: score = 1/(k + rank_in_dense) + 1/(k + rank_in_bm25)
    Docs missing from one list get penalty rank = length of that list.
    """
    scores = {}
    dense_penalty = len(dense)
    bm25_penalty  = len(bm25)

    for rank, chunk in enumerate(dense):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rank + 1)

    for rank, chunk in enumerate(bm25):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rank + 1)

    # Penalise docs that only appear in one list
    dense_ids = {c["id"] for c in dense}
    bm25_ids  = {c["id"] for c in bm25}

    for chunk in dense:
        if chunk["id"] not in bm25_ids:
            scores[chunk["id"]] += 1 / (k + bm25_penalty + 1)

    for chunk in bm25:
        if chunk["id"] not in dense_ids:
            scores[chunk["id"]] += 1 / (k + dense_penalty + 1)

    id_to_chunk = {c["id"]: c for c in dense + bm25}
    return [id_to_chunk[id] for id, _ in
            sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if id in id_to_chunk]


if __name__ == "__main__":
    query = "how do I get my money back"
    print(f"Query: '{query}'\n")

    chunks = load_all_chunks()
    bm25_results  = bm25_simple(chunks, query, expand=True)   # synonym expansion on
    dense_results = dense_retrieve(query, top_k=20)            # wider net for dense
    fused_results = reciprocal_rank_fusion(dense_results, bm25_results)

    print("=== DENSE ONLY (top 5) ===")
    for i, c in enumerate(dense_results[:5]):
        print(f"  [{i+1}] {c['doc_name']} (chunk {c['chunk_index']}) sim={c.get('similarity','?')}")

    print("\n=== BM25 ONLY (top 5) — with synonym expansion ===")
    for i, c in enumerate(bm25_results[:5]):
        print(f"  [{i+1}] {c['doc_name']} (chunk {c['chunk_index']})")

    print("\n=== FUSED / RRF (top 5) ===")
    for i, c in enumerate(fused_results[:5]):
        print(f"  [{i+1}] {c['doc_name']} (chunk {c['chunk_index']})")

    target = "01_return_policy.md"
    dense_rank = next((i+1 for i, c in enumerate(dense_results) if c["doc_name"] == target), None)
    bm25_rank  = next((i+1 for i, c in enumerate(bm25_results)  if c["doc_name"] == target), None)
    fused_rank = next((i+1 for i, c in enumerate(fused_results) if c["doc_name"] == target), None)
    print(f"\n{target}:")
    print(f"  Dense rank : {dense_rank or 'not in top-20'}")
    print(f"  BM25 rank  : {bm25_rank  or 'not found'}")
    print(f"  Fused rank : {fused_rank or 'not in results'}")
