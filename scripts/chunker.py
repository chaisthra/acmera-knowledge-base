"""
Chunking strategies for Week 2 — A1.

Three strategies:
  fixed_size       — naive 500-char fixed chunks (baseline, same as ingest.py)
  sliding_window   — fixed-size with overlap to avoid hard boundary cuts
  sentence_aware   — paragraph-aware, keeps logical units together

Usage from ingest.py:
  from chunker import get_chunker
  chunk_fn = get_chunker("sliding_window")
  chunks = chunk_fn(text)

CLI (re-ingest with a strategy):
  python scripts/ingest.py --strategy sliding_window
"""

CHUNK_SIZE = 500
OVERLAP = 100


def fixed_size_chunk(text, chunk_size=CHUNK_SIZE):
    """Original naive chunker — no overlap, hard cuts every 500 chars."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def sliding_window_chunk(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    """
    Fixed-size chunks with overlap between adjacent chunks.
    Each new chunk starts (chunk_size - overlap) characters after
    the previous one — eliminating hard boundary cuts.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += chunk_size - overlap
    return [c for c in chunks if c]


def sentence_aware_chunk(text, chunk_size=CHUNK_SIZE):
    """
    Split on double newlines (paragraph breaks), then merge small
    paragraphs until the size threshold is reached.
    Keeps numbered lists and policy conditions in the same chunk.
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks, current, current_len = [], [], 0

    for para in paragraphs:
        if current_len + len(para) + 2 > chunk_size and current:
            chunks.append('\n\n'.join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para) + 2

    if current:
        chunks.append('\n\n'.join(current))

    return chunks


STRATEGIES = {
    "fixed_size":     fixed_size_chunk,
    "sliding_window": sliding_window_chunk,
    "sentence_aware": sentence_aware_chunk,
}


def get_chunker(strategy: str):
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{strategy}'. Choose from: {list(STRATEGIES)}")
    return STRATEGIES[strategy]
