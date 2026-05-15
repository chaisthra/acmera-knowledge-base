# PII Anonymizer — Wired into ask()

## Pipeline Flow

```
User query (raw)
    │
    ▼
check_input()          ← blocks injections, off-topic, harmful intent
    │
    ▼
PiiAnonymizer.anonymize()   ← replaces EMAIL, PHONE, PERSON, ORDER_ID with placeholders
    │
    ▼
embed_query(clean_query)    ← embedding on anonymized text
    │
    ▼
retrieve / hybrid / rerank  ← retrieval on anonymized text
    │
    ▼
generate(clean_query, context)  ← LLM never sees raw PII
    │
    ▼
anonymizer.restore(answer)  ← placeholders replaced back with original values
    │
    ▼
check_output()              ← PII scan on restored answer as safety net
    │
    ▼
Final answer to user
```

## pii_redacted: true Test

Queries containing PII return `pii_redacted: true` in the response:

| Query | pii_redacted |
|-------|-------------|
| "My email is priya@gmail.com, order ORD-445521" | true |
| "Call me at +91 9876543210 about my return" | true |
| "What is the return window for electronics?" | false |

---

## Langfuse: Log Anonymized or Original Query?

**Log the anonymized query.**

The original query containing `priya@gmail.com` or `+91 9876543210` should never appear in Langfuse traces. Reasons:

1. **Compliance** — GDPR/DPDP require personal data to be minimized. Logging raw PII to a third-party observability platform (Langfuse, hosted externally) creates a data processing agreement requirement and a breach surface.

2. **Model training risk** — If Langfuse data is ever used for fine-tuning or evaluation, raw PII propagates into training sets.

3. **Breach impact** — If Langfuse credentials are compromised, anonymized traces expose no personal data.

The `pii_redacted: true` flag in trace metadata tells you the original query had PII without storing what it was.
