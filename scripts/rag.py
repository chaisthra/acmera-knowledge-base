"""
Core RAG pipeline with LangFuse tracing.

Week 1: naive dense retrieval
Week 2: hybrid retrieval — BM25 (rank_bm25) + dense + RRF fusion

Run:
  python scripts/rag.py                   # dense (default)
  python scripts/rag.py --mode hybrid     # hybrid
"""
import os
import json
import time
import argparse
import litellm
from openai import OpenAI
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
import psycopg2
from pgvector.psycopg2 import register_vector
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()
langfuse = Langfuse()

TOP_K = 5
BM25_CANDIDATES = TOP_K * 3   # wider net before RRF fusion
GENERATION_MODEL = "gpt-4o-mini"
FALLBACK_MODELS  = ["gpt-3.5-turbo"]

SYSTEM_PROMPT = """You are a helpful customer support assistant for Acmera, an Indian e-commerce company.
Answer the customer's question based on the provided context from our documentation.

Rules:
- Only answer based on the provided context. If the context doesn't contain enough information, say so.
- Be specific and cite relevant policy details (days, amounts, conditions).
- If the question involves membership tiers, check the context for tier-specific policies.
- Be concise but thorough.

Context from Acmera documentation:
{context}"""

STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for", "of", "and",
    "or", "but", "not", "with", "my", "i", "me", "we", "you", "he", "she",
    "they", "this", "that", "do", "did", "does", "how", "what", "when",
    "where", "why", "can", "will", "if", "be", "been", "have", "has", "had",
    "are", "was", "were", "by", "from", "as", "so", "up", "out", "get", "got",
}

SYNONYMS = {
    "money":      {"refund", "reimbursement", "cashback", "credit"},
    "back":       {"return", "returns", "returning"},
    "refund":     {"money", "back", "return", "reimburse"},
    "return":     {"back", "send", "refund"},
    "cheap":      {"discount", "offer", "sale", "promo"},
    "broken":     {"damaged", "defective", "faulty", "repair"},
    "fix":        {"repair", "troubleshoot", "resolve"},
    # account / security queries use "safe" but docs use "security"
    "safe":       {"security", "secure", "authentication", "protected"},
    "secure":     {"safe", "security", "authentication"},
    "protect":    {"secure", "safety", "security"},
}


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


# =========================================================================
# DENSE RETRIEVAL
# =========================================================================

@observe(name="query_embedding")
def embed_query(query):
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    return response.data[0].embedding


@observe(name="retrieval_dense")
def retrieve(query_embedding, top_k=TOP_K):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, doc_name, chunk_index, content, metadata,
                  1 - (embedding <=> %s::vector) AS similarity
           FROM chunks ORDER BY embedding <=> %s::vector LIMIT %s""",
        (query_embedding, query_embedding, top_k),
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

    langfuse_context.update_current_observation(metadata={
        "mode": "dense", "top_k": top_k,
        "results": [{"doc_name": r["doc_name"], "chunk_index": r["chunk_index"],
                     "similarity": r["similarity"]} for r in results],
    })
    return results


# =========================================================================
# BM25 RETRIEVAL
# =========================================================================

def _load_all_chunks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, doc_name, chunk_index, content, metadata FROM chunks ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"id": r[0], "doc_name": r[1], "chunk_index": r[2], "content": r[3],
         "metadata": r[4] if isinstance(r[4], dict) else json.loads(r[4])}
        for r in rows
    ]


def build_bm25_index():
    all_chunks = _load_all_chunks()
    tokenized = [c["content"].lower().split() for c in all_chunks]
    return BM25Okapi(tokenized), all_chunks


def _bm25_retrieve(query, bm25, all_chunks, top_k, expansion_threshold=1.0):
    """
    Raw BM25 retrieval with adaptive synonym expansion.
    First scores without expansion — if top score is below threshold,
    the query has weak keyword signal (vocabulary mismatch) so synonyms
    are added. Strong keyword matches skip expansion to avoid noise.
    """
    base_tokens = [t for t in query.lower().split() if t not in STOP_WORDS]

    raw_scores = bm25.get_scores(base_tokens)
    top_raw = max(raw_scores) if len(raw_scores) > 0 else 0

    if top_raw < expansion_threshold:
        expanded = list(base_tokens)
        for t in base_tokens:
            expanded.extend(SYNONYMS.get(t, []))
        scores = bm25.get_scores(expanded)
    else:
        scores = raw_scores

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for idx, score in ranked:
        if score > 0:
            chunk = all_chunks[idx].copy()
            chunk["bm25_score"] = round(float(score), 4)
            results.append(chunk)
    return results


# =========================================================================
# RECIPROCAL RANK FUSION
# =========================================================================

def reciprocal_rank_fusion(dense, bm25_results, top_k=TOP_K, k=60):
    """
    RRF score = 1/(k + rank_in_dense) + 1/(k + rank_in_bm25)
    Docs appearing in only one list get a penalty contribution
    from the other list using rank = len(that list).
    """
    scores = {}
    chunk_map = {}
    dense_penalty = len(dense)
    bm25_penalty  = len(bm25_results)

    for rank, chunk in enumerate(dense):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        chunk_map[cid] = chunk

    for rank, chunk in enumerate(bm25_results):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        if cid not in chunk_map:
            chunk_map[cid] = chunk

    dense_ids = {c["id"] for c in dense}
    bm25_ids  = {c["id"] for c in bm25_results}

    for chunk in dense:
        if chunk["id"] not in bm25_ids:
            scores[chunk["id"]] += 1.0 / (k + bm25_penalty + 1)

    for chunk in bm25_results:
        if chunk["id"] not in dense_ids:
            scores[chunk["id"]] += 1.0 / (k + dense_penalty + 1)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for cid, rrf_score in ranked:
        chunk = chunk_map[cid].copy()
        chunk["rrf_score"] = round(rrf_score, 6)
        results.append(chunk)
    return results


# =========================================================================
# HYBRID RETRIEVAL
# =========================================================================

@observe(name="retrieval_hybrid")
def hybrid_retrieve(query, query_embedding, top_k=TOP_K):
    """
    1. Dense retrieval (BM25_CANDIDATES wide)
    2. BM25 retrieval with synonym expansion (BM25_CANDIDATES wide)
    3. RRF fusion with penalty for single-list docs → top_k final
    retrieve.__wrapped__ is called to avoid double-tracing inside this observation.
    """
    bm25, all_chunks = build_bm25_index()
    dense_results = retrieve.__wrapped__(query_embedding, top_k=BM25_CANDIDATES)
    bm25_results  = _bm25_retrieve(query, bm25, all_chunks, top_k=BM25_CANDIDATES)
    fused = reciprocal_rank_fusion(dense_results, bm25_results, top_k=top_k)

    langfuse_context.update_current_observation(metadata={
        "mode": "hybrid",
        "dense_candidates": len(dense_results),
        "bm25_candidates": len(bm25_results),
        "results": [{"doc_name": r["doc_name"], "rrf_score": r.get("rrf_score")} for r in fused],
    })
    return fused


# =========================================================================
# CONTEXT ASSEMBLY + GENERATION
# =========================================================================

@observe(name="context_assembly")
def assemble_context(retrieved_chunks):
    context_parts = []
    for chunk in retrieved_chunks:
        context_parts.append(
            f"[Source: {chunk['doc_name']}, Chunk {chunk['chunk_index']}]\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_parts)
    langfuse_context.update_current_observation(metadata={
        "num_chunks": len(retrieved_chunks),
        "total_context_chars": len(context),
    })
    return context


@observe(name="generation")
def generate(query, context):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": query},
    ]
    response = litellm.completion(
        model=GENERATION_MODEL,
        fallbacks=FALLBACK_MODELS,
        messages=messages,
        temperature=0.1,
        max_tokens=1000,
    )
    answer = response.choices[0].message.content
    model_used = response.model or GENERATION_MODEL
    langfuse_context.update_current_observation(
        input=messages, output=answer,
        metadata={"model": model_used,
                  "prompt_tokens": response.usage.prompt_tokens,
                  "completion_tokens": response.usage.completion_tokens},
        usage={"input": response.usage.prompt_tokens,
               "output": response.usage.completion_tokens,
               "total": response.usage.total_tokens, "unit": "TOKENS"},
    )
    return answer


# =========================================================================
# PUBLIC API
# =========================================================================

@observe(name="rag_pipeline")
def ask(query, mode="dense"):
    start_time = time.time()
    langfuse_context.update_current_trace(
        input=query, metadata={"pipeline": f"rag_{mode}", "top_k": TOP_K}
    )

    query_embedding = embed_query(query)

    if mode == "hybrid":
        retrieved_chunks = hybrid_retrieve(query, query_embedding)
    else:
        retrieved_chunks = retrieve(query_embedding)

    context = assemble_context(retrieved_chunks)
    answer = generate(query, context)

    elapsed = round(time.time() - start_time, 2)
    langfuse_context.update_current_trace(
        output=answer, metadata={"elapsed_seconds": elapsed, "mode": mode}
    )
    trace_id = langfuse_context.get_current_trace_id()
    langfuse.flush()

    return {
        "query": query, "answer": answer,
        "retrieved_chunks": retrieved_chunks, "context": context,
        "trace_id": trace_id, "elapsed_seconds": elapsed,
    }


def ask_hybrid(query):
    return ask(query, mode="hybrid")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dense", "hybrid"], default="dense")
    parser.add_argument("--query", default="What is the standard return window for products?")
    args = parser.parse_args()

    result = ask(args.query, mode=args.mode)
    print(f"\nQuery : {result['query']}")
    print(f"Mode  : {args.mode}")
    print(f"Answer: {result['answer']}")
    print(f"Trace : {result['trace_id']}")
    print(f"Time  : {result['elapsed_seconds']}s")
    for i, c in enumerate(result["retrieved_chunks"]):
        score_key = "rrf_score" if "rrf_score" in c else "similarity"
        print(f"  [{i+1}] {c['doc_name']} (chunk {c['chunk_index']}) — {score_key}: {c.get(score_key)}")
