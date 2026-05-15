"""
Semantic Cache — Session 4

In-memory cache for RAG answers. On each query:
  1. Embed the query
  2. Compare against all stored embeddings via cosine similarity
  3. If similarity >= threshold, return cached answer (skip retrieval + generation)
  4. Otherwise run the full pipeline and store the result

Run demo:
  python scripts/semantic_cache.py
"""
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()


class SemanticCache:
    def __init__(self, threshold=0.92):
        self.threshold = threshold
        self.entries = []  # list of {embedding, query, answer}

    def _cosine(self, a, b):
        a, b = np.array(a), np.array(b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm == 0:
            return 0.0
        return float(np.dot(a, b) / norm)

    def get(self, query_embedding, debug=False):
        """
        Returns cached entry if any stored embedding is above threshold.
        Returns None on miss.
        """
        best_sim, best = 0.0, None
        for entry in self.entries:
            sim = self._cosine(query_embedding, entry["embedding"])
            if debug:
                print(f"    sim={sim:.4f} vs \"{entry['query']}\"")
            if sim > best_sim:
                best_sim, best = sim, entry
        if best_sim >= self.threshold:
            return {"answer": best["answer"], "query": best["query"],
                    "cache_similarity": round(best_sim, 4)}
        if debug and best:
            print(f"    best={best_sim:.4f} — below threshold {self.threshold}")
        return None

    def set(self, query, embedding, answer):
        embedding = np.array(embedding)
        embedding = embedding / np.linalg.norm(embedding)
        self.entries.append({"query": query, "embedding": embedding.tolist(), "answer": answer})

    def size(self):
        return len(self.entries)


# =========================================================================
# GPTCACHE DEMO
# Run:  python scripts/semantic_cache.py
# =========================================================================

if __name__ == "__main__":
    import time
    from gptcache import cache
    from gptcache.adapter.adapter import adapt
    from gptcache.manager import CacheBase, VectorBase, get_data_manager
    from gptcache.similarity_evaluation.distance import SearchDistanceEvaluation
    from gptcache.processor.pre import get_prompt

    EMBED_MODEL = "text-embedding-3-small"
    EMBED_DIM   = 1536  # text-embedding-3-small output dimension

    def _embed(text, **kwargs):
        resp = client.embeddings.create(model=EMBED_MODEL, input=text)
        vec = np.array(resp.data[0].embedding)
        return (vec / np.linalg.norm(vec)).tolist()

    print("Initialising GPTCache (SQLite + FAISS, OpenAI embeddings)...")
    cache.init(
        pre_embedding_func=get_prompt,   # extracts 'prompt' kwarg passed to adapt()
        embedding_func=_embed,
        data_manager=get_data_manager(
            CacheBase("sqlite"),
            VectorBase("faiss", dimension=EMBED_DIM),
        ),
        similarity_evaluation=SearchDistanceEvaluation(),
    )

    SYSTEM = (
        "You are a helpful customer support assistant for Acmera, "
        "an Indian e-commerce company. Answer in one sentence."
    )

    # GPTCache's adapt() handles embedding + search + store.
    # We wire in the OpenAI v1 client on cache miss via llm_func.
    def _llm(prompt, **kwargs):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user",   "content": prompt},
            ],
        )
        return resp.choices[0].message.content

    def _cache_convert(cache_data):
        return cache_data  # stored as plain string

    def _update_cache(llm_data, update_func, **kwargs):
        update_func(llm_data)
        return llm_data

    def ask_cached(query):
        # adapt() extracts the 'prompt' kwarg for embedding + cache lookup,
        # calls _llm only on a cache miss, then stores the result.
        return adapt(_llm, _cache_convert, _update_cache, prompt=query)

    # Same 5 pairs from threshold analysis
    PAIRS = [
        ("What is the return window?",       "What is the return period?"),
        ("Do you accept UPI?",               "Can I pay using UPI?"),
        ("How do I track my order?",         "How can I track my order?"),
        ("What is the membership fee?",      "What is the cost of membership?"),
        ("How do I cancel my order?",        "How can I cancel my order?"),
    ]

    cold_times, warm_times = [], []

    print("\n" + "=" * 75)
    print("ROUND 1 — cold queries (cache empty)")
    print("=" * 75)
    for cold, _ in PAIRS:
        t0 = time.time()
        answer = ask_cached(cold)
        elapsed = round(time.time() - t0, 3)
        cold_times.append(elapsed)
        print(f"  [{elapsed:6.3f}s] COLD  Q: {cold}")
        print(f"              A: {answer[:90]}")

    print("\n" + "=" * 75)
    print("ROUND 2 — warm queries (similar paraphrases — expect cache hits)")
    print("=" * 75)
    for _, warm in PAIRS:
        t0 = time.time()
        answer = ask_cached(warm)
        elapsed = round(time.time() - t0, 3)
        warm_times.append(elapsed)
        hit_label = "HIT " if elapsed < 0.5 else "MISS"
        print(f"  [{elapsed:6.3f}s] {hit_label}  Q: {warm}")
        print(f"              A: {answer[:90]}")

    avg_cold = sum(cold_times) / len(cold_times)
    avg_warm = sum(warm_times) / len(warm_times)
    speedup  = round(avg_cold / avg_warm, 1) if avg_warm > 0 else float("inf")

    print("\n" + "=" * 75)
    print("RESPONSE TIME COMPARISON")
    print("=" * 75)
    print(f"  {'Query':<45} {'cold':>8}  {'warm':>8}")
    print(f"  {'-'*45} {'--------':>8}  {'--------':>8}")
    for (cold, _), ct, wt in zip(PAIRS, cold_times, warm_times):
        print(f"  {cold:<45} {ct:>8.3f}s  {wt:>8.3f}s")
    print(f"  {'AVERAGE':<45} {avg_cold:>8.3f}s  {avg_warm:>8.3f}s")
    print(f"\n  Speedup on cached queries: {speedup}×")
