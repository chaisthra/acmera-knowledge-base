# A1 Chunking Strategy Comparison
**Date:** 2026-05-03 | **Queries:** 50 | **Chunk size:** 500 | **Overlap (sliding):** 100

---

## Summary Scores

| Metric             | fixed_size | sentence_aware | sliding_window |
|--------------------|:----------:|:--------------:|:--------------:|
| Total chunks       | 100        | 118            | 119            |
| Retrieval hit rate | 98%        | 98%            | 98%            |
| MRR                | 0.89       | 0.88           | 0.88           |
| Avg faithfulness   | 4.94 / 5   | 4.94 / 5       | 4.96 / 5       |
| **Avg correctness**| **4.48**   | **4.60**       | **4.64** ✓     |

---

## Correctness by Category

| Category       | fixed_size | sentence_aware | sliding_window | Winner          |
|----------------|:----------:|:--------------:|:--------------:|-----------------|
| account        | 4.00       | 4.33           | 4.33           | sentence / slide |
| business       | 5.00       | 5.00           | 5.00           | tie             |
| membership     | 4.60       | 4.60           | 4.60           | tie             |
| orders         | 5.00       | 5.00           | 5.00           | tie             |
| payments       | 4.43       | **4.86**       | 4.57           | sentence_aware  |
| products       | 4.25       | **4.75**       | 4.50           | sentence_aware  |
| promotions     | 4.33       | 4.33           | **4.67**       | sliding_window  |
| refunds        | 4.00       | **5.00**       | **5.00**       | sentence / slide |
| returns        | 4.62       | 4.50           | **4.75**       | sliding_window  |
| rewards        | 4.33       | 4.33           | 4.33           | tie             |
| shipping       | 4.40       | **5.00**       | **5.00**       | sentence / slide |
| sustainability | 4.00       | 4.00           | 4.00           | tie             |
| warranty       | **4.60**   | 4.00           | 4.40           | fixed_size      |

---

## Correctness by Difficulty

| Difficulty | fixed_size | sentence_aware | sliding_window |
|------------|:----------:|:--------------:|:--------------:|
| easy       | 4.52       | 4.62           | 4.62           |
| medium     | 4.43       | 4.57           | **4.67**       |

---

## Analysis (~100 words)

Sliding window achieves the highest overall correctness (4.64/5) by ensuring policy details that span chunk boundaries appear in at least one complete chunk. Fixed-size chunking hurts most on payments (4.43) and products (4.25), where key details get split mid-sentence. Sentence-aware excels on payments (4.86) by keeping payment method lists intact, but underperforms on warranty (4.00) where policy conditions span multiple paragraphs beyond the 500-char threshold. Warranty is the only category where fixed-size wins (4.60) — likely because warranty docs have compact, self-contained paragraphs. All three strategies tie on retrieval hit rate (98%); chunking differences surface in generation quality, not retrieval.
