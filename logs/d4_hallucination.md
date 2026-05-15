# O2.1 Hallucination Detector

## Test Output

| # | Label | Expected | Detected | Pass? | Unsupported Claims |
|---|-------|----------|----------|-------|--------------------|
| 1 | GROUNDED | False | False | ✓ | - |
| 2 | GROUNDED | False | False | ✓ | - |
| 3 | GROUNDED | False | False | ✓ | - |
| 4 | HALLUCINATED | True | True | ✓ | "Premium Platinum members get 90-day return window" |
| 5 | HALLUCINATED | True | True | ✓ | "2-year extended warranty for Premium Gold"; "Refunds in 24 hours" |
| 6 | HALLUCINATED | True | True | ✓ | "COD for all orders regardless of amount"; "Ships to Dubai and Singapore" |

**Result: 6/6 correct (100%). False positive rate: 0/3.**

---

## False Positive Analysis

No grounded claims were flagged as ungrounded. All three hallucinated answers were correctly caught.

This 0% false positive rate on a small controlled test is encouraging but should not be over-interpreted. The grounded test cases were written to closely mirror the context — real answers may include reasonable inference or paraphrasing that the judge could flag as unsupported even when the intent is grounded. For example, if the context says "returns accepted within 30 days" and the answer says "you have a month to return," a strict judge might mark "one month" as unsupported because the exact phrasing differs.

LLM-as-judge reliability degrades when: (1) the context is long and the claim is buried, (2) the answer paraphrases rather than quotes, (3) the claim involves arithmetic or inference from multiple context sentences. At production scale, false positive rates of 5–15% are realistic — meaning 1 in 10–20 correct answers gets flagged and handed off to a human unnecessarily. This makes the confidence threshold a tuning parameter, not a fixed value.
