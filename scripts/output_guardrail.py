"""
Output guardrails — hallucination detection and confidence checking.

Run:
  python scripts/output_guardrail.py
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

PII_PATTERNS = None  # lazy-loaded

def check_output(answer: str) -> dict:
    """
    Scan answer for PII before it reaches the user.
    Returns {safe: bool, pii_types: list, redacted: str}
    """
    import re
    patterns = {
        "phone":   r"\b[6-9]\d{9}\b",
        "email":   r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "pan":     r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        "card":    r"\b(?:\d[ -]?){15,16}\b",
    }
    found = []
    redacted = answer
    for pii_type, pattern in patterns.items():
        if re.search(pattern, redacted):
            found.append(pii_type)
            redacted = re.sub(pattern, f"[{pii_type.upper()} REDACTED]", redacted)
    return {"safe": len(found) == 0, "pii_types": found, "redacted": redacted}


HALLUCINATION_PROMPT = """You are a fact-checking judge.

Given a context and an answer, identify every factual claim in the answer.
For each claim, state whether it is SUPPORTED or UNSUPPORTED by the context.
A claim is SUPPORTED only if the context explicitly states it — do not infer or assume.

Context: {context}

Answer: {answer}

Respond with JSON only, no markdown:
{{"claims": [{{"claim": str, "supported": bool, "evidence": str}}], "has_hallucination": bool}}"""


def check_hallucination(answer: str, context: str) -> dict:
    """
    Returns {has_hallucination: bool, claims: list, unsupported_claims: list}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": HALLUCINATION_PROMPT.format(context=context, answer=answer),
        }],
        temperature=0,
        max_tokens=800,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    result = json.loads(raw)
    result["unsupported_claims"] = [c for c in result["claims"] if not c["supported"]]
    return result


# =========================================================================
# TEST CASES
# =========================================================================

CONTEXT = """
Acmera offers two membership tiers: Premium Silver and Premium Gold.
Premium Silver members get a 45-day return window.
Premium Gold members get a 60-day return window.
Standard customers have a 30-day return window.
Electronics come with a 1-year manufacturer warranty.
Acmera does not offer extended warranties beyond the manufacturer warranty.
Cash on delivery is available for orders under Rs. 5,000.
International shipping is not available — Acmera ships within India only.
Refunds are processed within 5-7 business days after the return is received.
""".strip()

TEST_CASES = [
    # --- GROUNDED (drawn directly from corpus) ---
    {
        "label": "GROUNDED",
        "answer": "Premium Silver members get a 45-day return window, while Premium Gold members get 60 days. Standard customers have 30 days.",
        "expected": False,
    },
    {
        "label": "GROUNDED",
        "answer": "Acmera ships within India only — international shipping is not available. Cash on delivery is available for orders under Rs. 5,000.",
        "expected": False,
    },
    {
        "label": "GROUNDED",
        "answer": "Refunds take 5-7 business days after the return is received. Electronics come with a 1-year manufacturer warranty.",
        "expected": False,
    },
    # --- HALLUCINATED (plausible but not in corpus) ---
    {
        "label": "HALLUCINATED",
        "answer": "Premium Platinum members get a 90-day return window and free return shipping on all orders.",
        "expected": True,
    },
    {
        "label": "HALLUCINATED",
        "answer": "Acmera offers a 2-year extended warranty on all electronics for Premium Gold members. Refunds are processed within 24 hours.",
        "expected": True,
    },
    {
        "label": "HALLUCINATED",
        "answer": "Cash on delivery is available for all orders regardless of amount. International shipping is available to Dubai and Singapore.",
        "expected": True,
    },
]


if __name__ == "__main__":
    print(f"\n{'#':<3} {'Label':<12} {'Expected':<10} {'Detected':<10} {'Pass?':<6} {'Unsupported Claims'}")
    print("-" * 110)

    passed = 0
    for i, case in enumerate(TEST_CASES, 1):
        result = check_hallucination(case["answer"], CONTEXT)
        detected = result["has_hallucination"]
        correct = detected == case["expected"]
        if correct:
            passed += 1
        mark = "✓" if correct else "✗"
        unsupported = "; ".join(c["claim"][:60] for c in result["unsupported_claims"]) or "-"
        print(f"{i:<3} {case['label']:<12} {str(case['expected']):<10} {str(detected):<10} {mark:<6} {unsupported[:70]}")

    print("-" * 110)
    print(f"\nResult: {passed}/6 correct ({passed/6:.0%})")

    grounded_flagged = sum(
        1 for i, case in enumerate(TEST_CASES)
        if case["label"] == "GROUNDED" and check_hallucination(case["answer"], CONTEXT)["has_hallucination"]
    )
    print(f"False positive rate (grounded flagged as hallucinated): {grounded_flagged}/3")
