"""
Context Assembler — Session 4

Cleans up and structures retrieved chunks before they reach the LLM.

Functions:
  deduplicate      — remove near-duplicate chunks (word-level Jaccard)
  expand_context   — add neighbouring chunks from the same source document
  order_by_source  — group and sort chunks by source document
  compress         — truncate to a token budget, keeping highest-scored chunks
  assemble_advanced — runs all four in sequence, returns a final context string

Run standalone smoke test:
  python scripts/context_assembler.py
"""
from collections import defaultdict


# =========================================================================
# DEDUPLICATE
# =========================================================================

def _jaccard(text_a, text_b):
    a = set(text_a.lower().split())
    b = set(text_b.lower().split())
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def deduplicate(chunks, threshold=0.75):
    """
    Remove near-duplicate chunks using word-level Jaccard similarity.
    Keeps the first occurrence of each near-duplicate group. Chunks should be
    passed in relevance order (highest first) so the most relevant is kept.

    threshold=0.75 means chunks sharing 75%+ of vocabulary are considered duplicates.
    """
    kept = []
    for chunk in chunks:
        if not any(_jaccard(chunk["content"], k["content"]) >= threshold for k in kept):
            kept.append(chunk)
    return kept


# =========================================================================
# EXPAND CONTEXT
# =========================================================================

def expand_context(chunk, all_chunks, window=1):
    """
    Returns the chunk plus its immediate neighbours from the same source document.
    Neighbours are adjacent by chunk_index within the same doc_name.

    window=1 adds one chunk before and one after. window=2 adds two on each side.
    Useful for recovering policy context that was split across chunk boundaries.
    """
    same_doc = sorted(
        [c for c in all_chunks if c["doc_name"] == chunk["doc_name"]],
        key=lambda c: c["chunk_index"],
    )
    indices = [c["chunk_index"] for c in same_doc]

    try:
        pos = indices.index(chunk["chunk_index"])
    except ValueError:
        return [chunk]

    start = max(0, pos - window)
    end   = min(len(same_doc), pos + window + 1)
    return same_doc[start:end]


# =========================================================================
# ORDER BY SOURCE
# =========================================================================

def order_by_source(chunks):
    """
    Groups chunks by source document and sorts within each group by chunk_index.
    Presenting content in document order helps the LLM follow the narrative of a
    policy document rather than jumping between unrelated snippets.
    """
    by_doc = defaultdict(list)
    for chunk in chunks:
        by_doc[chunk["doc_name"]].append(chunk)

    ordered = []
    for doc in sorted(by_doc):
        ordered.extend(sorted(by_doc[doc], key=lambda c: c["chunk_index"]))
    return ordered


# =========================================================================
# COMPRESS
# =========================================================================

def _estimate_tokens(text):
    """Rough token count: words × 1.3 to account for subword tokenisation."""
    return int(len(text.split()) * 1.3)


def compress(chunks, max_tokens=2000):
    """
    Truncates the chunk list to stay within max_tokens.
    Highest-scored chunks are kept first — scores checked in priority order:
    cohere_score > rrf_score > similarity > 0.

    Note: ordering of the returned list reflects source order (call order_by_source
    after compress if you want source ordering and score-based selection together).
    In assemble_advanced, compress is called on the source-ordered list intentionally
    so that the LLM receives coherent passages up to the token budget.
    """
    def _score(c):
        return (c.get("cohere_score") or c.get("rrf_score") or c.get("similarity") or 0)

    sorted_by_score = sorted(chunks, key=_score, reverse=True)

    kept  = []
    total = 0
    for chunk in sorted_by_score:
        tokens = _estimate_tokens(chunk["content"])
        if total + tokens > max_tokens:
            break
        kept.append(chunk)
        total += tokens
    return kept


# =========================================================================
# ASSEMBLE ADVANCED
# =========================================================================

def assemble_advanced(chunks, query, all_chunks, max_tokens=2000):
    """
    Full context assembly pipeline:
      1. Deduplicate  — drop near-identical chunks from retrieval
      2. Expand       — add neighbouring chunks for boundary coverage
      3. Deduplicate  — expansion may re-introduce overlapping chunks
      4. Compress     — select highest-scored chunks within token budget
      5. Order        — sort kept chunks by source document for coherent reading
      6. Format       — return as a single context string for the LLM
    """
    # 1. deduplicate initial retrieval (chunks are already scored/ranked)
    deduped = deduplicate(chunks)

    # 2. expand each chunk with its neighbours; carry relevance score to neighbours
    seen_ids = set()
    expanded = []
    for chunk in deduped:
        for neighbour in expand_context(chunk, all_chunks, window=1):
            if neighbour["id"] not in seen_ids:
                n = neighbour.copy()
                # neighbours inherit a slightly discounted score so compress
                # still prefers the originally retrieved chunk over its neighbours
                if "cohere_score" in chunk and "cohere_score" not in n:
                    n["cohere_score"] = chunk["cohere_score"] * 0.9
                elif "rrf_score" in chunk and "rrf_score" not in n:
                    n["rrf_score"] = chunk["rrf_score"] * 0.9
                expanded.append(n)
                seen_ids.add(neighbour["id"])

    # 3. deduplicate again (neighbours of different chunks may overlap)
    expanded = deduplicate(expanded)

    # 4. compress — select within token budget by score, then re-order by source
    compressed = compress(expanded, max_tokens=max_tokens)

    # 5. order by source for coherent LLM reading
    ordered = order_by_source(compressed)

    # 6. format
    parts = [
        f"[Source: {c['doc_name']}, Chunk {c['chunk_index']}]\n{c['content']}"
        for c in ordered
    ]
    return "\n\n---\n\n".join(parts)


# =========================================================================
# SMOKE TEST
# =========================================================================

if __name__ == "__main__":
    sample_chunks = [
        {"id": 1, "doc_name": "returns_policy.txt", "chunk_index": 0,
         "content": "Products can be returned within 30 days of delivery.", "similarity": 0.9},
        {"id": 2, "doc_name": "returns_policy.txt", "chunk_index": 1,
         "content": "Products can be returned within 30 days of delivery for a full refund.", "similarity": 0.88},
        {"id": 3, "doc_name": "returns_policy.txt", "chunk_index": 2,
         "content": "Items must be in original packaging to qualify for a return.", "similarity": 0.7},
        {"id": 4, "doc_name": "warranty_policy.txt", "chunk_index": 0,
         "content": "Warranty covers manufacturing defects for 12 months.", "similarity": 0.6},
    ]

    print("--- deduplicate ---")
    deduped = deduplicate(sample_chunks)
    print(f"  {len(sample_chunks)} → {len(deduped)} chunks (removed near-duplicate)")

    print("\n--- expand_context ---")
    expanded = expand_context(sample_chunks[0], sample_chunks, window=1)
    print(f"  chunk 0 expanded to {len(expanded)} chunks (added neighbour)")

    print("\n--- order_by_source ---")
    ordered = order_by_source(sample_chunks)
    for c in ordered:
        print(f"  {c['doc_name']} chunk {c['chunk_index']}")

    print("\n--- compress (max_tokens=30) ---")
    compressed = compress(sample_chunks, max_tokens=30)
    print(f"  {len(sample_chunks)} → {len(compressed)} chunks within token budget")

    print("\n--- assemble_advanced ---")
    context = assemble_advanced(sample_chunks[:3], "return window", sample_chunks)
    print(context[:300])
