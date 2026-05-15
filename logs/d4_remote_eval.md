# D4.1 Remote Eval — Deployed API vs Local

## Dense Mode (65 queries)

| Metric | Local | Remote | Delta |
|--------|-------|--------|-------|
| Retrieval hit rate | 98.5% | 98% | -0.5% |
| Avg MRR | 0.90 | 0.93 | +0.03 |
| Avg faithfulness | 4.94 / 5 | 4.84 / 5 | -0.10 |
| Avg correctness | 4.74 / 5 | 4.73 / 5 | -0.01 |

---

## Advanced Mode (remote: 64 queries, local: 65 queries)

| Metric | Local | Remote | Delta |
|--------|-------|--------|-------|
| Retrieval hit rate | 96.9% | 96.9% | 0.00% |
| Avg MRR | 0.92 | 0.93 | +0.01 |
| Avg faithfulness | 4.98 / 5 | 4.94 / 5 | -0.04 |
| Avg correctness | 4.65 / 5 | 4.68 / 5 | +0.03 |

---

## Category Breakdown — Dense

| Category | Local Hit% | Remote Hit% | Local Correct | Remote Correct |
|----------|-----------|-------------|---------------|----------------|
| account | 100% | 100% | 4.50 | 4.67 |
| business | 100% | 100% | 5.00 | 5.00 |
| membership | 100% | 100% | 4.67 | 4.50 |
| orders | 100% | 100% | 5.00 | 5.00 |
| payments | 100% | 100% | 4.71 | 4.43 |
| products | 100% | 100% | 4.88 | 4.88 |
| promotions | 100% | 100% | 4.33 | 4.67 |
| refunds | 100% | 100% | 4.00 | 5.00 |
| returns | 90% | 100% | 4.50 | 4.70 |
| rewards | 100% | 100% | 4.25 | 4.75 |
| shipping | 100% | 100% | 4.80 | 5.00 |
| support | 100% | 100% | 5.00 | 5.00 |
| sustainability | 100% | 100% | 4.67 | 5.00 |
| warranty | 100% | 86% | 4.43 | 4.57 |

---

## Category Breakdown — Advanced

| Category | Local Hit% | Remote Hit% | Local Correct | Remote Correct |
|----------|-----------|-------------|---------------|----------------|
| account | 100% | 100% | 4.50 | 4.50 |
| business | 100% | 100% | 5.00 | 5.00 |
| membership | 100% | 100% | 4.67 | 4.67 |
| orders | 100% | 100% | 5.00 | 5.00 |
| payments | 100% | 100% | 4.71 | 4.57 |
| products | 100% | 100% | 4.88 | 4.75 |
| promotions | 100% | 100% | 4.33 | 4.67 |
| refunds | 100% | 100% | 4.00 | 5.00 |
| returns | 90% | 90% | 4.50 | 4.70 |
| rewards | 100% | 100% | 4.25 | 4.50 |
| shipping | 100% | 100% | 4.80 | 4.80 |
| support | 100% | 100% | 5.00 | 5.00 |
| sustainability | 100% | 100% | 4.67 | 4.67 |
| warranty | 100% | 100% | 4.43 | 4.43 |

---

## Conclusion

Both dense and advanced modes show remote scores within the LLM-as-judge noise floor (±0.2) of local scores. No quality regression introduced by deployment. Category-level variance (e.g. refunds flipping correctness by 1.0) is expected for n=1 categories where a single query drives the entire category score.
