"""
Rerankers — Session 4

Two implementations:
  1. cross_encoder_demo  — educational only. Embeds query+doc as a combined string,
                           scores by cosine similarity vs query-only embedding.
                           Run against bi_encoder_rank for one query to see the diff.

  2. CohereReranker      — production. Calls co.rerank() which runs a real cross-encoder
                           on Cohere's side. Far more accurate than embedding similarity.

Run:
  python scripts/reranker.py
"""
import os
import math
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()


# =========================================================================
# HELPERS
# =========================================================================

def _cosine(a, b):
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _embed(texts):
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]


# =========================================================================
# BI-ENCODER BASELINE
# =========================================================================

def bi_encoder_rank(query, chunks, top_k=5):
    """
    Standard bi-encoder: embed query and each chunk separately, rank by cosine sim.
    This is what dense retrieval already does — included here only as comparison baseline
    for the cross-encoder demo.
    """
    query_emb = _embed([query])[0]
    doc_embs  = _embed([c["content"] for c in chunks])

    scored = []
    for chunk, doc_emb in zip(chunks, doc_embs):
        c = chunk.copy()
        c["bi_encoder_score"] = round(_cosine(query_emb, doc_emb), 6)
        scored.append(c)

    scored.sort(key=lambda x: x["bi_encoder_score"], reverse=True)
    return scored[:top_k]


# =========================================================================
# CROSS-ENCODER DEMO (OpenAI embeddings — educational only)
# =========================================================================

def cross_encoder_demo(query, chunks, top_k=5):
    """
    Simulates a cross-encoder using OpenAI embeddings.

    Idea: a real cross-encoder jointly encodes query+document in a single forward pass,
    giving it the ability to capture fine-grained interaction between query tokens and
    document tokens. Here we approximate this by concatenating query+document into one
    string, embedding it, and scoring by cosine similarity against the query-only embedding.

    This is NOT a true cross-encoder — it still uses a bi-encoder model (text-embedding-3-small).
    The joint string gives the embedding model more context to work with, but it doesn't
    replicate the token-level attention that makes real cross-encoders powerful.

    Use this only to understand the concept. Use CohereReranker for real reranking.
    """
    query_emb = _embed([query])[0]
    combined_texts = [f"{query}\n\n{c['content']}" for c in chunks]
    combined_embs  = _embed(combined_texts)

    scored = []
    for chunk, comb_emb in zip(chunks, combined_embs):
        c = chunk.copy()
        c["cross_encoder_score"] = round(_cosine(comb_emb, query_emb), 6)
        scored.append(c)

    scored.sort(key=lambda x: x["cross_encoder_score"], reverse=True)
    return scored[:top_k]


# =========================================================================
# COHERE RERANKER (production)
# =========================================================================

class CohereReranker:
    """
    Production reranker using Cohere's rerank API.

    Cohere runs a true cross-encoder on their side — every query+document pair is
    evaluated jointly with full attention, producing a relevance score that's
    significantly more accurate than cosine similarity on pre-computed embeddings.

    Requires COHERE_API_KEY in environment.
    """

    MODEL = "rerank-v4.0-pro"

    def __init__(self):
        import cohere
        self.co = cohere.ClientV2(os.getenv("COHERE_API_KEY"))

    def rerank(self, query, chunks, top_k=5):
        """
        Reranks chunks using Cohere's rerank API.
        Returns top_k chunks sorted by relevance with cohere_score attached.
        Sleep between calls to stay within trial key limit (10 calls/min).
        """
        import time
        if not chunks:
            return []

        time.sleep(6)  # trial key: 10 calls/min → 1 per 6s
        response = self.co.rerank(
            model=self.MODEL,
            query=query,
            documents=[c["content"] for c in chunks],
            top_n=top_k,
        )

        reranked = []
        for result in response.results:
            chunk = chunks[result.index].copy()
            chunk["cohere_score"] = round(result.relevance_score, 6)
            reranked.append(chunk)

        return reranked


# =========================================================================
# DEMO — run from command line to compare bi-encoder vs cross-encoder
# =========================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from rag import _load_all_chunks

    QUERY = "What happens if my product is damaged during return shipping?"
    TOP_K = 5
    SAMPLE_SIZE = 30  # subset of corpus for speed

    print(f"Query: {QUERY}\n")
    print("Loading chunks from database...")
    all_chunks = _load_all_chunks()
    sample = all_chunks[:SAMPLE_SIZE]

    print(f"Ranking {len(sample)} sample chunks...\n")

    bi_results = bi_encoder_rank(QUERY, sample, top_k=TOP_K)
    ce_results = cross_encoder_demo(QUERY, sample, top_k=TOP_K)

    print("=" * 70)
    print(f"{'Rank':<5} {'BI-ENCODER':^30} {'CROSS-ENCODER DEMO':^30}")
    print(f"{'':5} {'doc / score':^30} {'doc / score':^30}")
    print("-" * 70)
    for i, (bi, ce) in enumerate(zip(bi_results, ce_results), 1):
        bi_label = f"{bi['doc_name'][:20]} ({bi['bi_encoder_score']:.4f})"
        ce_label = f"{ce['doc_name'][:20]} ({ce['cross_encoder_score']:.4f})"
        changed  = " ← reranked" if bi["doc_name"] != ce["doc_name"] else ""
        print(f"  {i:<3} {bi_label:<30} {ce_label:<30}{changed}")
    print("=" * 70)
    print("\nDifferences show where joint encoding changes the ranking.")
    print("For production quality, use CohereReranker() — it runs a real cross-encoder.")
