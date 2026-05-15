"""
Reversible PII anonymizer — scoped to one request.
Never share an instance across requests.

Run:
  python scripts/pii_anonymizer.py
"""
import re
import uuid
import json
import hashlib
from datetime import datetime, timezone
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


# Custom recognizer for Acmera order IDs (ORD-XXXXXX)
_order_recognizer = PatternRecognizer(
    supported_entity="ORDER_ID",
    patterns=[Pattern(name="order_id", regex=r"\bORD-\d{4,10}\b", score=0.9)],
)

_BRAND_ALLOWLIST = {"acmera", "amazon", "flipkart", "meesho", "myntra", "snapdeal"}

_analyzer  = AnalyzerEngine()
_analyzer.registry.add_recognizer(_order_recognizer)
_anonymizer = AnonymizerEngine()


AUDIT_LOG_PATH = "audit.jsonl"


def redaction_audit_log(
    trace_id: str,
    pii_types: list,
    query_hash: str,
    intent: str = None,
) -> None:
    """
    Append a PII detection event to the audit log.
    NEVER stores the original query or PII values.
    """
    entry = {
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "trace_id":        trace_id,
        "pii_types":       pii_types,
        "query_hash":      query_hash,
        "intent":          intent,
        "retention_days":  30,
        "data_principal_notified": False,
    }
    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


class PiiAnonymizer:
    """
    Reversible PII anonymizer scoped to one request.
    Never share an instance across requests.
    """

    def __init__(self):
        self._map: dict[str, str] = {}       # placeholder → original value
        self.detected_types: list[str] = []  # PII entity types found

    def anonymize(self, text: str) -> str:
        results = _analyzer.analyze(
            text=text,
            entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "ORDER_ID"],
            language="en",
        )
        # Filter out brand names falsely detected as PERSON
        results = [
            r for r in results
            if not (r.entity_type == "PERSON"
                    and text[r.start:r.end].lower() in _BRAND_ALLOWLIST)
        ]

        if not results:
            return text

        # Sort by start position descending so replacements don't shift indices
        results = sorted(results, key=lambda r: r.start, reverse=True)
        self.detected_types = list({r.entity_type for r in results})
        chars = list(text)
        for r in results:
            original = text[r.start:r.end]
            placeholder = f"<{r.entity_type}_{uuid.uuid4().hex[:6].upper()}>"
            self._map[placeholder] = original
            chars[r.start:r.end] = list(placeholder)

        return "".join(chars)

    def restore(self, text: str) -> str:
        for placeholder, original in self._map.items():
            text = text.replace(placeholder, original)
        return text


# =========================================================================
# DEMO
# =========================================================================

if __name__ == "__main__":
    import os

    # Clear previous audit log for clean test
    if os.path.exists(AUDIT_LOG_PATH):
        os.remove(AUDIT_LOG_PATH)

    queries_with_pii = [
        "My email is priya@gmail.com, order ORD-445521",
        "Call me at +91 9876543210 about my return for ORD-112233",
        "I'm Rahul Mehta and I was charged twice — please check",
        "Send the invoice to ops@techcorp.in for order ORD-998877",
        "My number is 9845012345 and my order ORD-334455 is missing",
        "Please email me at customer@gmail.com about ORD-667788",
        "Arun Kumar here, I need help with ORD-223344",
        "Reach me at 8765432109 for the refund status",
        "I am Deepa and my email deepa@yahoo.com needs updating",
        "Call 9988776655 regarding my complaint for ORD-554433",
    ]

    queries_without_pii = [
        "What is the standard return window?",
        "How do I track my order?",
        "What payment methods are accepted?",
        "Does Acmera ship internationally?",
        "What is the warranty on electronics?",
        "How do I reach Premium Gold membership?",
        "What items cannot be returned?",
        "How long do refunds take?",
        "Can I cancel an order after it ships?",
        "What are the Premium Silver benefits?",
    ]

    all_queries = (
        [(q, True) for q in queries_with_pii]
        + [(q, False) for q in queries_without_pii]
    )

    print(f"\n{'#':<3} {'Has PII':<9} {'PII Found':<8} {'Types':<30} {'Query'[:50]}")
    print("-" * 100)

    for i, (query, has_pii) in enumerate(all_queries, 1):
        anon = PiiAnonymizer()
        clean = anon.anonymize(query)
        found = clean != query

        if found:
            query_hash = hashlib.sha256(query.encode()).hexdigest()
            redaction_audit_log(
                trace_id=f"test-{i:02d}",
                pii_types=anon.detected_types,
                query_hash=query_hash,
                intent="test",
            )

        types_str = ", ".join(anon.detected_types) if anon.detected_types else "-"
        mark = "✓" if found == has_pii else "✗"
        print(f"{i:<3} {str(has_pii):<9} {mark} {str(found):<6} {types_str:<30} {query[:50]}")

    # Verify audit log
    print(f"\n{'='*60}")
    audit_entries = []
    if os.path.exists(AUDIT_LOG_PATH):
        with open(AUDIT_LOG_PATH) as f:
            audit_entries = [json.loads(line) for line in f]

    print(f"Audit log entries: {len(audit_entries)} (expected 10)")
    print(f"All entries have pii_types: {all('pii_types' in e for e in audit_entries)}")
    print(f"No raw PII in log: {not any(any(v in json.dumps(e) for v in ['@gmail', '9876543210', 'Rahul']) for e in audit_entries)}")
    print(f"\nSample entry:\n{json.dumps(audit_entries[0], indent=2) if audit_entries else 'none'}")
