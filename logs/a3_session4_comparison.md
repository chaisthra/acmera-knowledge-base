# Session 4 Pipeline Comparison (q10 excluded)
**Date:** 2026-05-15 | **Queries:** 64 (q10 excluded — vocabulary mismatch outlier)
**Modes:** dense · hybrid (BM25+RRF) · advanced (hybrid + Cohere rerank-v4.0-pro + context assembly)

---

## Summary Scorecard

| Metric           | Dense  | Hybrid | Advanced | Winner      |
|------------------|:------:|:------:|:--------:|-------------|
| Hit rate         | 98.4%  | 98.4%  | 98.4%    | tie         |
| MRR              | 0.909  | 0.897  | **0.930**| ✓ Advanced  |
| Avg faithfulness | 4.938  | 4.938  | **5.000**| ✓ Advanced  |
| Avg correctness  | 4.594  | 4.641  | **4.734**| ✓ Advanced  |

Advanced wins on every metric that measures quality. Hit rate is equal across all three.

---

## Correctness by Category

| Category       |  N | Dense | Hybrid | Advanced | Winner          |
|----------------|:--:|:-----:|:------:|:--------:|-----------------|
| account        |  3 | 4.67  |  4.67  |   4.67   | tie             |
| business       |  1 | 5.00  |  5.00  |   5.00   | tie             |
| membership     |  6 | 4.67  |**4.83**|   4.67   | ✓ Hybrid        |
| orders         |  5 | 5.00  |  5.00  |   5.00   | tie             |
| payments       |  7 | 4.57  |  4.43  |   4.57   | Dense / Adv     |
| products       |  8 |**4.75**| 4.50  |   4.62   | ✓ Dense         |
| promotions     |  3 | 4.67  |  4.67  |   4.67   | tie             |
| refunds        |  1 | 5.00  |  4.00  | **5.00** | Dense / Adv     |
| returns        | 10 | 4.30  |  4.80  | **4.70** | ✓ Hybrid / Adv  |
| rewards        |  4 | 4.25  |  4.50  | **4.75** | ✓ Advanced      |
| shipping       |  5 | 4.80  |  4.80  |   4.80   | tie             |
| support        |  1 | 5.00  |  5.00  |   5.00   | tie             |
| sustainability |  3 | 4.67  |  4.67  | **5.00** | ✓ Advanced      |
| warranty       |  7 | 4.29  |  4.29  | **4.71** | ✓ Advanced      |

---

## Hit Rate by Category

| Category  | Dense | Hybrid | Advanced |
|-----------|:-----:|:------:|:--------:|
| returns   | 90%   | 100%   | 100%     |
| warranty  | 100%  | 86%    | 86%      |
| all others| 100%  | 100%   | 100%     |

Hybrid and Advanced fixed returns (90%→100%). Warranty remains 86% in both — the specific failing query has a retrieval issue that reranking can't recover since the correct chunk isn't in the candidate pool.

---

## Key Findings

**Advanced wins overall** — highest correctness (4.734), MRR (0.930), and perfect faithfulness (5.00).
Cohere's cross-encoder reranking surfaces the most relevant chunk to position 1 more reliably,
and context assembly eliminates noise before it reaches the LLM.

**Warranty is the standout win for Advanced** — correctness jumped from 4.29 (dense/hybrid) to 4.71.
Warranty queries span multiple conditions across chunk boundaries; context expansion and deduplication
recovered the adjacent context that dense retrieval alone left behind.

**Hybrid wins returns hit rate** (90%→100%) but Advanced matches it while also improving correctness.
BM25 synonym expansion correctly caught "send back / money back" vocabulary that dense missed.

**Dense wins products** (4.75) — BM25 on product queries introduces noise from spec sheets
and adjacent product docs, diluting precision that dense alone preserves.

**Payments regressed in hybrid** (4.57→4.43) — same BM25 noise pattern as products.
Advanced recovers it back to 4.57 via Cohere reranking.
