"""
LiteLLM fallback test.

Test 1: bad primary model → expect fallback to gpt-3.5-turbo
Test 2: real query through rag.py → confirm litellm.completion() works end-to-end

Run:
  python scripts/test_litellm_fallback.py
"""
import os
import sys
import litellm
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

MESSAGES = [{"role": "user", "content": "Reply with exactly three words: fallback is working."}]

# ── Test 1: bad primary model, fallback to gpt-3.5-turbo ─────────────────────
print("=" * 60)
print("TEST 1 — bad model name, fallback to gpt-3.5-turbo")
print("=" * 60)
try:
    response = litellm.completion(
        model="gpt-this-model-does-not-exist",
        fallbacks=["gpt-3.5-turbo"],
        messages=MESSAGES,
    )
    print(f"  Model used : {response.model}")
    print(f"  Answer     : {response.choices[0].message.content.strip()}")
    print("  RESULT     : PASS — fallback triggered successfully\n")
except Exception as e:
    print(f"  RESULT     : FAIL — exception not caught by fallback: {e}\n")

# ── Test 2: normal ask() call through rag.py ─────────────────────────────────
print("=" * 60)
print("TEST 2 — normal ask() through rag.py with litellm")
print("=" * 60)
try:
    from rag import ask
    result = ask("What is the standard return window for products?", mode="dense")
    print(f"  Answer     : {result['answer'][:120]}...")
    print(f"  Trace ID   : {result['trace_id']}")
    print("  RESULT     : PASS — litellm integration end-to-end working\n")
except Exception as e:
    print(f"  RESULT     : FAIL — {e}\n")
