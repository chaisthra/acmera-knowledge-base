# A3 Pipeline Mode Comparison
**Date:** 2026-05-15 | **Queries:** 65 | **Modes:** dense · hybrid · advanced (hybrid + Cohere rerank-v4.0-pro + context assembly)

---

## Summary Scorecard

| Metric             | Dense  | Hybrid | Advanced | Winner   |
|--------------------|:------:|:------:|:--------:|----------|
| Retrieval hit rate | 98.5%  | 96.9%  | 96.9%    | ✓ Dense  |
| Avg MRR            | 0.90   | 0.88   | **0.92** | ✓ Adv    |
| Avg faithfulness   | 4.94   | 4.89   | **5.00** | ✓ Adv    |
| **Avg correctness**| **4.74** | 4.62 | 4.63     | ✓ Dense  |

---

## Correctness by Category

| Category       | Dense  | Hybrid | Advanced | Winner          |
|----------------|:------:|:------:|:--------:|-----------------|
| account        | **4.75** | 3.75 | 3.75     | ✓ Dense         |
| business       | 5.00   | 5.00   | 5.00     | tie             |
| membership     | 4.67   | **4.83** | 4.67   | ✓ Hybrid        |
| orders         | 5.00   | 5.00   | 5.00     | tie             |
| payments       | 4.57   | 4.57   | 4.29     | tie (dense/hyb) |
| products       | **4.75** | 4.62 | 4.62     | ✓ Dense         |
| promotions     | 4.67   | 4.67   | 4.67     | tie             |
| refunds        | 5.00   | 4.00   | **5.00** | Dense / Adv     |
| returns        | **4.90** | 4.80 | 4.70     | ✓ Dense         |
| rewards        | 4.50   | 4.50   | **4.75** | ✓ Advanced      |
| shipping       | 4.80   | 4.80   | 4.80     | tie             |
| support        | 5.00   | 5.00   | 5.00     | tie             |
| sustainability | 4.67   | 4.67   | **5.00** | ✓ Advanced      |
| warranty       | 4.57   | 4.29   | **4.57** | Dense / Adv     |

---

## Faithfulness by Category

| Category       | Dense  | Hybrid | Advanced |
|----------------|:------:|:------:|:--------:|
| account        | 5.00   | 4.75   | **5.00** |
| products       | 4.88   | 4.75   | **5.00** |
| returns        | 4.80   | 5.00   | **5.00** |
| warranty       | 4.86   | 4.43   | **5.00** |
| *(all others)* | 5.00   | 5.00   | **5.00** |

Advanced achieves perfect faithfulness (5.00) across every category.

---

## Hit Rate & MRR by Category

| Category   | Dense Hit | Hybrid Hit | Adv Hit | Dense MRR | Hybrid MRR | Adv MRR |
|------------|:---------:|:----------:|:-------:|:---------:|:----------:|:-------:|
| account    | **100%**  | 75%        | 75%     | **0.81**  | 0.75       | 0.75    |
| returns    | 90%       | **100%**   | **100%**| 0.72      | 0.76       | **0.93**|
| warranty   | **100%**  | 86%        | 86%     | 0.86      | 0.75       | **0.86**|
| promotions | 100%      | 100%       | 100%    | 0.83      | 0.53       | **0.75**|
| rewards    | 100%      | 100%       | 100%    | 1.00      | 1.00       | **0.88**|

---

## Analysis

Dense retrieval wins overall correctness (4.74) because it avoids the vocabulary mismatch that hurts hybrid and advanced on the `account` category — "safe" vs "security" pulls the wrong chunk to rank 1, which neither Cohere reranking nor context assembly can recover from because the right chunk was never retrieved in the first place. Garbage in, garbage out: reranking can only sort what was fetched.

Advanced wins on faithfulness (perfect 5.00) and MRR (0.92). Cohere's cross-encoder reranking surfaces the most relevant chunk to position 1 more reliably (returns MRR jumped from 0.72 dense → 0.93 advanced), and the context assembly pipeline eliminates the noise chunks that cause hallucinations. That's why faithfulness is perfect even in categories where correctness is lower.

The MRR improvement in `returns` (0.72 → 0.93) is the clearest win: hybrid fixed the hit rate (90% → 100%) and Cohere's reranker promoted the most relevant chunk to rank 1, recovering the MRR gap dense had from pulling the right document but wrong chunk first.

**Bottom line:** advanced is the strongest pipeline for precision (faithfulness, MRR) but dense remains better for recall (hit rate, overall correctness) until the account vocabulary mismatch is fixed upstream in retrieval.

---

## Worst Category Per Mode

| Mode     | Worst Category | Correctness | Hit Rate | Root Cause                              |
|----------|---------------|:-----------:|:--------:|----------------------------------------|
| Dense    | rewards       | 4.50        | 100%     | Rewards policy has edge cases          |
| Hybrid   | account       | 3.75        | 75%      | Vocabulary mismatch — "safe" vs "security" |
| Advanced | account       | 3.75        | 75%      | Same root cause, reranker can't fix missing chunks |
