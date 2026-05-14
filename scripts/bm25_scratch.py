"""
BM25 from scratch — A2.1

Simplified BM25: tokenise by whitespace + lowercase, score chunks by
how many query tokens appear in the chunk.
Supports stop word filtering, synonym expansion, length normalization, and IDF weighting.

Run:
  python scripts/bm25_scratch.py
"""
import os
import sys
import json
import math
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))


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


def load_all_chunks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, doc_name, chunk_index, content, metadata FROM chunks")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    chunks = []
    for row in rows:
        chunks.append({
            "id": row[0],
            "doc_name": row[1],
            "chunk_index": row[2],
            "content": row[3],
            "metadata": row[4] if isinstance(row[4], dict) else json.loads(row[4]),
        })
    return chunks


STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "not", "with", "my", "i", "me", "we", "you", "he", "she",
    "they", "this", "that", "do", "did", "does", "how", "what", "when",
    "where", "why", "can", "will", "if", "be", "been", "have", "has", "had",
    "are", "was", "were", "by", "from", "as", "so", "up", "out", "get", "got",
}


SYNONYMS = {
    "money":    {"refund", "reimbursement", "cashback", "credit"},
    "back":     {"return", "returns", "returning"},
    "refund":   {"money", "back", "return", "reimburse"},
    "return":   {"back", "send", "refund"},
    "cheap":    {"discount", "offer", "sale", "promo"},
    "broken":   {"damaged", "defective", "faulty", "repair"},
    "fix":      {"repair", "troubleshoot", "resolve"},
}


def bm25_simple(chunks, query, expand=False, normalize=True, use_idf=True):
    """
    Simplified BM25: score chunks by query token matches.
    - expand=True   : synonym expansion on query tokens
    - normalize=True: divide score by chunk length (penalizes verbose chunks)
    - use_idf=True  : weight rare terms higher than common ones
                      IDF(t) = log(N / chunks_containing_t + 1)
    Returns chunks sorted by score (highest first), zero-score excluded.
    """
    query_tokens = {t for t in query.lower().split() if t not in STOP_WORDS}
    if expand:
        expanded = set(query_tokens)
        for t in query_tokens:
            expanded.update(SYNONYMS.get(t, set()))
        query_tokens = expanded
    if not query_tokens:
        return []

    N = len(chunks)

    # precompute IDF for each query token
    idf = {}
    if use_idf:
        for token in query_tokens:
            df = sum(1 for c in chunks if token in c["content"].lower().split())
            idf[token] = math.log(N / (df + 1))
    else:
        for token in query_tokens:
            idf[token] = 1.0   # flat weight — same as old behaviour

    scored = []
    for chunk in chunks:
        chunk_tokens = chunk["content"].lower().split()
        score = sum(idf[t] for t in chunk_tokens if t in query_tokens)
        if normalize and chunk_tokens:
            score /= len(chunk_tokens)
        scored.append((score, chunk))

    return [c for score, c in sorted(scored, key=lambda x: x[0], reverse=True) if score > 0]


if __name__ == "__main__":
    print("Loading chunks from database...")
    chunks = load_all_chunks()
    print(f"Loaded {len(chunks)} chunks.\n")

    query = "how do I get my money back"
    print(f"Query: '{query}'")
    print(f"Query tokens (after stop word filter): {sorted({t for t in query.lower().split() if t not in STOP_WORDS})}\n")

    results = bm25_simple(chunks, query, expand=True, normalize=True, use_idf=True)

    print(f"Top results ({len(results)} total matches):")
    print("-" * 70)
    for i, chunk in enumerate(results[:3]):
        query_tokens = {t for t in query.lower().split() if t not in STOP_WORDS}
        chunk_tokens = chunk["content"].lower().split()
        matched = sorted({t for t in chunk_tokens if t in query_tokens})
        print(f"[{i+1}] {chunk['doc_name']} (chunk {chunk['chunk_index']})")
        print(f"     Matched tokens: {matched}")
        print(f"     Preview: {chunk['content'][:120].strip()}...")
        print()

    found = any(c["doc_name"] == "01_return_policy.md" for c in results[:3])
    print(f"01_return_policy.md in top-3: {'YES' if found else 'NO — vocabulary mismatch'}")
