# Audit Log for PII Events

## Test Run Results (20 queries)

| # | Has PII | Detected | Types | Notes |
|---|---------|----------|-------|-------|
| 1 | True | True | ORDER_ID, EMAIL_ADDRESS | Correct |
| 2 | True | True | PHONE_NUMBER, ORDER_ID | Correct |
| 3 | True | True | PERSON | Correct |
| 4 | True | True | ORDER_ID, EMAIL_ADDRESS | Correct |
| 5 | True | True | PHONE_NUMBER, ORDER_ID | Correct |
| 6 | True | True | PERSON, ORDER_ID, EMAIL_ADDRESS | Correct |
| 7 | True | True | PERSON, ORDER_ID | Correct |
| 8 | True | True | PHONE_NUMBER | Correct |
| 9 | True | True | PERSON, EMAIL_ADDRESS | Correct |
| 10 | True | True | PHONE_NUMBER, ORDER_ID | Correct |
| 11 | False | False | - | Correct |
| 12 | False | False | - | Correct |
| 13 | False | False | - | Correct |
| 14 | False | **True** | PERSON | **False positive** — "Acmera" detected as a person name |
| 15 | False | False | - | Correct |
| 16 | False | False | - | Correct |
| 17 | False | False | - | Correct |
| 18 | False | False | - | Correct |
| 19 | False | False | - | Correct |
| 20 | False | False | - | Correct |

**Audit log entries: 11 (10 genuine + 1 false positive). No raw PII values in log. All entries have pii_types. ✓**

### Sample audit.jsonl entry
```json
{
  "timestamp": "2026-05-15T17:28:17.199253+00:00",
  "trace_id": "test-01",
  "pii_types": ["ORDER_ID", "EMAIL_ADDRESS"],
  "query_hash": "ddb9ce78...",
  "intent": "test",
  "retention_days": 30,
  "data_principal_notified": false
}
```

---

## India's DPDPA Obligations for AI Systems

Under the **Digital Personal Data Protection Act (DPDPA) 2023**, a company processing personal data through an AI system must:

1. **Consent** — Obtain clear, specific consent before processing personal data. Users must know their query data is processed by an AI system.

2. **Purpose limitation** — Data collected for customer support cannot be used for model training or analytics without separate consent.

3. **Data minimisation** — Only collect and process what is necessary. Sending raw PII to an LLM when anonymized text achieves the same result violates this principle — hence the anonymizer.

4. **Data Principal rights** — Users have the right to access, correct, and erase their personal data. The `data_principal_notified` field in the audit log tracks notification obligations.

5. **Data Fiduciary obligations** — The company is the Data Fiduciary and must implement reasonable security safeguards, maintain processing records, and report breaches within 72 hours.

6. **Significant Data Fiduciary** — If the system scales to millions of users, additional obligations apply: Data Protection Impact Assessment (DPIA), Data Protection Officer appointment, and annual audits.

---

## Additional Field for Regulatory Compliance

**Field to add: `"processing_purpose": str`**

For a regulatory review, auditors need to know *why* the PII was processed — e.g. `"customer_support_query"`, `"order_lookup"`, `"refund_request"`. This maps to DPDPA's purpose limitation requirement: each processing event must be justified by a specific, documented purpose. Without it, the audit log proves PII was seen but not *why*, which fails a compliance review. A `"legal_basis"` field (e.g. `"consent"` or `"legitimate_interest"`) would also be required.
