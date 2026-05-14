# A2.3 Hybrid Search Eval Delta
**Date:** 2026-05-04 | **Queries:** 50 | **Strategy:** sliding_window | **Baseline:** 2026-05-02 (65q)

---

## Summary Scorecard

| Metric             | Dense  | Hybrid | Delta     |
|--------------------|:------:|:------:|:---------:|
| Retrieval hit rate | 98%    | 96%    | -2pp      |
| MRR                | 0.88   | 0.84   | -0.04     |
| Avg faithfulness   | 4.90   | 4.88   | -0.02     |
| **Avg correctness**| **4.60** | **4.52** | **-0.08** |

---

## Correctness by Category

| Category       | Dense  | Hybrid | Delta  | Winner  |
|----------------|:------:|:------:|:------:|---------|
| account        | 4.33   | 3.33   | -1.00  | ✗ Dense |
| business       | 5.00   | 5.00   | 0.00   | tie     |
| membership     | 4.60   | 4.80   | +0.20  | ✓ Hybrid |
| orders         | 5.00   | 5.00   | 0.00   | tie     |
| payments       | 4.43   | 4.57   | +0.14  | ✓ Hybrid |
| products       | 4.50   | 4.00   | -0.50  | ✗ Dense |
| promotions     | 4.67   | 4.67   | 0.00   | tie     |
| refunds        | 5.00   | 5.00   | 0.00   | tie     |
| **returns**    | **4.75** | **4.88** | **+0.13** | ✓ Hybrid |
| rewards        | 4.33   | 4.67   | +0.34  | ✓ Hybrid |
| shipping       | 4.80   | 4.80   | 0.00   | tie     |
| sustainability | 4.00   | 4.00   | 0.00   | tie     |
| warranty       | 4.40   | 3.80   | -0.60  | ✗ Dense |

---

## Hit Rate by Category

| Category   | Dense | Hybrid | Delta |
|------------|:-----:|:------:|:-----:|
| account    | 100%  | 67%    | -33pp |
| returns    | 88%   | 100%   | +12pp |
| warranty   | 100%  | 80%    | -20pp |
| (all others) | 100% | 100% | 0pp  |

---

## Regression Check (vs 65q baseline saved 2026-05-02)

| Metric             | Baseline | Current (hybrid) | Delta   | Status |
|--------------------|:--------:|:----------------:|:-------:|--------|
| retrieval_hit_rate | 98.46%   | 96.00%           | -2.46pp | ✅ PASS |
| avg_faithfulness   | 98.77%   | 97.60%           | -1.17pp | ✅ PASS |
| avg_correctness    | 92.62%   | 90.40%           | -2.22pp | ✅ PASS |

**Result: NO REGRESSION (threshold: 5.0pp)**

---

## Analysis

Hybrid retrieval improved vocabulary-mismatch categories as expected:
- **returns +0.13** — hit rate jumped 88% → 100%; BM25 synonym expansion caught
  "send back / money back" queries that dense missed
- **rewards +0.34, membership +0.20, payments +0.14** — keyword signal from BM25
  boosted precision on structured policy questions

But BM25 hurt two categories:
- **account -1.00 correctness, -33pp hit rate** — q10 "Is the Acmera app safe to use?"
  collapsed to correct=1. BM25 synonym expansion pulled in security/account management
  chunks that displaced the right document
- **warranty -0.60 correctness, -20pp hit rate** — warranty queries use specific model
  names and technical terms; BM25 expansion introduced noise from adjacent tech docs

**Root cause:** the synonym table is too broad. "fix" → repair/troubleshoot/resolve
and "broken" → damaged/defective pulled in unrelated chunks for account and warranty
queries that don't benefit from those expansions.

**Next step:** scope synonyms to query intent, or apply expansion only when query
tokens have low BM25 scores without expansion.
