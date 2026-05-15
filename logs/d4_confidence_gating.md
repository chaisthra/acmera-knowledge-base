# O2.2 Confidence-Gated Answers

## Test Output (10 queries — 5 answerable, 5 ambiguous)

| # | Type | Query | Confidence | Handoff? | Reasoning |
|---|------|-------|------------|----------|-----------|
| 1 | Answerable | What is the return window for Premium Gold members? | high | no | Explicitly stated in context |
| 2 | Answerable | How long do refunds take? | high | no | Refund timeline explicitly in context |
| 3 | Answerable | Is cash on delivery available for a Rs. 3,000 order? | high | no | Policy explicitly covers orders under Rs. 5,000 |
| 4 | Answerable | Does Acmera ship internationally? | high | no | Explicitly stated — India only |
| 5 | Answerable | What is the warranty on electronics? | high | no | 1-year warranty explicitly in context |
| 6 | Ambiguous | Can I return a product after 90 days if I have a valid reason? | high | no | Return limits stated clearly — answered as "no" |
| 7 | Ambiguous | What is the return policy for Premium Platinum members? | **low** | **YES** | Platinum tier not in context |
| 8 | Ambiguous | Can I get a replacement instead of a refund for damaged goods? | **low** | **YES** | Replacements not mentioned in context |
| 9 | Ambiguous | Does the 60-day return window apply to sale items? | **low** | **YES** | No sale-item conditions in context |
| 10 | Ambiguous | What happens if the return courier loses my package? | **low** | **YES** | Lost courier scenario not covered |

**Result: 5/5 answerable → high confidence, 4/5 ambiguous → handoff (LOW). Q6 rated high — answered confidently as "no" since return limits are explicit.**

---

## Handoff Message

When confidence = LOW, the pipeline returns:

> "I want to give you accurate information, but I don't have enough context to answer this confidently. Please contact our support team at support@acmera.com for accurate help."

---

## Tuning the Confidence Threshold Using Langfuse

To find the optimal threshold, apply this filter in Langfuse:

```
Filter: scores.correctness < 3.0
Group by: metadata.confidence
```

This shows correctness score distribution per confidence level. The optimal threshold is the confidence level where `avg_correctness` drops below your acceptable floor (e.g. 3.5/5).

**Specific steps:**
1. In Langfuse → Traces, filter by `metadata.confidence = "medium"`
2. Look at the average correctness score for medium-confidence traces
3. If medium correctness < 3.5 on average → escalate medium to handoff (only serve high)
4. If medium correctness > 4.0 → medium is safe to serve, only handoff on LOW

This lets you tune empirically from real user traffic rather than guessing. The `conf_reasoning` field stored in each trace also lets you cluster why medium answers occur — corpus gaps vs. inference vs. ambiguous phrasing — and fix the root cause rather than just raising the threshold.
