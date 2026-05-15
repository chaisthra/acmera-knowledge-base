# D4 Guardrail Latency Measurement

## Latency Table (20 queries — deployed API, dense mode)

| # | Type | Query | Guard ms | Total ms | Guard % |
|---|------|-------|----------|----------|---------|
| 1 | Simple | What is the return window? | 1849.5 | 6666.5 | 27.7% |
| 2 | Simple | How do I track my order? | 530.7 | 2272.5 | 23.4% |
| 3 | Simple | What is the warranty period? | 1482.3 | 4327.4 | 34.3% |
| 4 | Simple | Can I cancel my order? | 1563.5 | 3682.7 | 42.5% |
| 5 | Simple | How do I update my address? | 2502.8 | 4450.7 | 56.2% |
| 6 | Simple | What payment methods are accepted? | 1577.0 | 4532.4 | 34.8% |
| 7 | Simple | Does Acmera ship to rural areas? | 1679.8 | 2834.4 | 59.3% |
| 8 | Simple | How do I redeem reward points? | 1404.1 | 2886.3 | 48.6% |
| 9 | Simple | What is Premium Gold membership? | 1363.7 | 4413.5 | 30.9% |
| 10 | Simple | How do I contact support? | 3415.5 | 5478.8 | 62.3% |
| 11 | Complex | I bought electronics 45 days ago, Premium Silver... | 1343.5 | 3729.1 | 36.0% |
| 12 | Complex | My order shows delivered but I never received it... | 1008.4 | 5549.8 | 18.2% |
| 13 | Complex | Tier-specific return windows for damaged goods... | 1893.7 | 5386.3 | 35.2% |
| 14 | Complex | Trying to upgrade to Premium Gold but threshold... | 2318.6 | 5024.7 | 46.1% |
| 15 | Complex | Return a product bought during a sale if opened... | 1224.4 | 3614.4 | 33.9% |
| 16 | Complex | Refund approved 10 days ago, not received... | 1502.7 | 6601.5 | 22.8% |
| 17 | Complex | Premium Silver — extended warranty on electronics? | 1773.0 | 4420.9 | 40.1% |
| 18 | Complex | Reward points if I return a product bought with points? | 1898.4 | 3625.1 | 52.4% |
| 19 | Complex | 3 items ordered, 2 arrived damaged — partial return? | 1704.8 | 4181.7 | 40.8% |
| 20 | Complex | Restocking fee for returning large appliances? | 834.8 | 2774.1 | 30.1% |
| **AVG** | | | **1643.6 ms** | **4322.6 ms** | **38.8%** |

---

## Key Findings

- Average guardrail cost: **1.6s** (two API calls: `is_on_topic` + safety classifier)
- Average total pipeline: **4.3s**
- Guardrail overhead: **38.8%** of total latency on average
- Range: 18.2% (complex, fast pipeline) to 62.3% (simple queries where pipeline is fast but guardrail is slow)

Simple queries show higher guard% because the RAG pipeline is faster for them — the guardrail's fixed ~1.6s cost dominates. Complex queries have a slower pipeline so the guard% is lower.

---

## Caching Analysis

At **38.8% average overhead**, guardrail caching is clearly worth it. The threshold where caching makes sense is roughly **>15%** overhead — beyond that, the complexity of a cache pays for itself in user experience.

### How to implement using SemanticCache

```python
from semantic_cache import SemanticCache
from openai import OpenAI

_guard_cache = SemanticCache(threshold=0.95)  # higher threshold — safety decisions need more precision
client = OpenAI()

def check_input_cached(query: str) -> dict:
    embedding = client.embeddings.create(
        model="text-embedding-3-small", input=query
    ).data[0].embedding

    cached = _guard_cache.get(embedding)
    if cached:
        return {"safe": cached["safe"], "category": cached["category"],
                "refusal": cached.get("refusal"), "cache_hit": True}

    result = check_input(query)
    _guard_cache.set(query, embedding, result)
    return result
```

**Threshold choice**: 0.95 (vs 0.92 for RAG answers) because safety decisions are binary — a near-identical query phrased slightly differently could have different intent, so we require higher similarity before reusing a cached decision.

**Expected savings**: Repeated queries (e.g. "what is the return window?" asked many times) would hit the cache after the first call, reducing guardrail cost from ~1.6s to ~200ms (just the embedding call). For a support chatbot where users ask the same questions repeatedly, cache hit rates of 30–50% are realistic.
