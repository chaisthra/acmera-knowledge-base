"""
Test confidence gating with 10 queries (5 answerable, 5 ambiguous).
Run: python scripts/test_confidence.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rag import generate, Confidence, HANDOFF_MESSAGE

CONTEXT = """
Acmera return policy: Standard customers have 30 days. Premium Silver members get 45 days.
Premium Gold members get 60 days. Returns must be in original packaging.
Electronics come with a 1-year manufacturer warranty.
Cash on delivery is available for orders under Rs. 5,000.
Refunds are processed within 5-7 business days after return is received.
International shipping is not available. Acmera ships within India only.
Premium Gold threshold: Rs. 1,00,000 annual spending.
Premium Silver threshold: Rs. 50,000 annual spending.
"""

QUERIES = [
    # 5 clearly answerable
    ("ANSWERABLE", "What is the return window for Premium Gold members?"),
    ("ANSWERABLE", "How long do refunds take?"),
    ("ANSWERABLE", "Is cash on delivery available for a Rs. 3,000 order?"),
    ("ANSWERABLE", "Does Acmera ship internationally?"),
    ("ANSWERABLE", "What is the warranty on electronics?"),
    # 5 ambiguous / out of scope
    ("AMBIGUOUS", "Can I return a product after 90 days if I have a valid reason?"),
    ("AMBIGUOUS", "What is the return policy for Premium Platinum members?"),
    ("AMBIGUOUS", "Can I get a replacement instead of a refund for damaged goods?"),
    ("AMBIGUOUS", "Does the 60-day return window apply to sale items?"),
    ("AMBIGUOUS", "What happens if the return courier loses my package?"),
]

print(f"\n{'#':<3} {'Type':<12} {'Query':<55} {'Confidence':<10} {'Handoff?':<9} Reasoning")
print("-" * 130)

for i, (qtype, query) in enumerate(QUERIES, 1):
    answer, confidence, reasoning = generate(query, CONTEXT)
    handoff = "YES" if confidence == Confidence.LOW else "no"
    print(f"{i:<3} {qtype:<12} {query[:53]:<55} {confidence.value:<10} {handoff:<9} {reasoning[:50]}")
