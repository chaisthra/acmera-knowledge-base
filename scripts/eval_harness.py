"""
Evaluation Harness — Sessions 1 & 2 Starter

SESSION 1 functions (implement during Session 1 homework):
  1. check_retrieval_hit() — is the expected source in the top-K results?
  2. calculate_mrr() — how high is the first relevant chunk ranked?
  3. judge_faithfulness() — is the answer grounded in the context? (LLM-as-judge)
  4. judge_correctness() — does the answer match the expected answer? (LLM-as-judge)
  5. run_eval() — orchestrate everything and produce a scorecard

SESSION 2 functions (implement during Session 2 homework):
  6. run_stratified_eval() — break down scores by category and difficulty
  7. attach_langfuse_scores() — attach eval scores to LangFuse traces
  8. save_baseline() — save current scores as baseline_scores.json

Run: python scripts/eval_harness.py
Run with options:
  python scripts/eval_harness.py --include-hard
  python scripts/eval_harness.py --save-baseline
  python scripts/eval_harness.py --category membership
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

SCRIPT_DIR = os.path.dirname(__file__)

# Import rag pipeline once eval is implemented
# from rag import ask


# =========================================================================
# GOLDEN DATASET
# =========================================================================

def load_golden_dataset():
    """Load the golden dataset from JSON file."""
    path = os.path.join(SCRIPT_DIR, "golden_dataset.json")
    if not os.path.exists(path):
        print("No golden_dataset.json found. Create one first!")
        return []
    with open(path) as f:
        return json.load(f)


# =========================================================================
# SESSION 1: RETRIEVAL METRICS
# =========================================================================

def check_retrieval_hit(retrieved_chunks, expected_source):
    """
    Is the expected source document in the retrieved chunks?
    Returns True/False.

    TODO: Implement in Session 1 homework.
    Hint: iterate retrieved_chunks, check if any chunk["doc_name"] == expected_source
    """
    return any(c["doc_name"] == expected_source for c in retrieved_chunks)


def calculate_mrr(retrieved_chunks, expected_source):
    """
    Mean Reciprocal Rank — how high is the first relevant chunk?
    Position 1 → 1.0, Position 3 → 0.33, Not found → 0.0

    Formula: 1 / rank_of_first_relevant_chunk

    TODO: Implement in Session 1 homework.
    """
    for rank, chunk in enumerate(retrieved_chunks, start=1):
        if chunk["doc_name"] == expected_source:
            return 1.0 / rank
    return 0.0


# =========================================================================
# SESSION 1: GENERATION METRICS (LLM-as-Judge)
# =========================================================================

def judge_faithfulness(query, answer, context):
    """
    Is the answer grounded in the retrieved context?
    Uses GPT-4o-mini as a judge with a structured rubric.
    Returns: {"score": 1-5, "reason": "explanation"}

    Judge prompt should ask:
    - Score 5: every claim explicitly supported by context
    - Score 3: some claims not in context
    - Score 1: fabricated information

    TODO: Implement in Session 1 homework.
    """
    prompt = f"""You are an evaluation judge. Score whether the answer is grounded in the provided context.

Rubric:
- Score 5: Every claim in the answer is explicitly supported by the context.
- Score 4: Almost all claims supported; minor unsupported details.
- Score 3: Some claims are supported but others are not in the context.
- Score 2: Most claims are not supported by the context.
- Score 1: Answer contains fabricated information not present in the context.

Question: {query}

Context:
{context}

Answer:
{answer}

Respond with JSON only, no markdown fences:
{{"score": <1-5>, "reason": "<one sentence explanation>"}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=200,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def judge_correctness(query, answer, expected_answer):
    """
    Does the answer match the expected answer?
    Uses GPT-4o-mini as a judge.
    Returns: {"score": 1-5, "reason": "explanation"}

    TODO: Implement in Session 1 homework.
    """
    pass


# =========================================================================
# SESSION 1: EVAL RUNNER
# =========================================================================

def run_eval(include_hard=False):
    """
    Run the full evaluation:
    1. Load golden dataset (+ hard queries if --include-hard)
    2. Run each query through the RAG pipeline via ask()
    3. Score retrieval (hit rate, MRR)
    4. Score generation (faithfulness, correctness)
    5. Print scorecard
    6. Save results to eval_results.json

    TODO: Implement in Session 1 homework.
    """
    pass


# =========================================================================
# SESSION 2: STRATIFIED EVALUATION
# =========================================================================

def run_stratified_eval(results):
    """
    Break down eval scores by category and by difficulty.

    For categories: group results by result["category"], compute
    hit_rate, faithfulness, correctness per group, print a table.

    For difficulty: group by result["difficulty"] (easy/medium/hard),
    compute correctness per group, print a table.

    The key insight: 87% overall might hide 40% on membership queries.
    Stratification surfaces this.

    TODO: Implement in Session 2 homework.
    """
    pass


# =========================================================================
# SESSION 2: LANGFUSE SCORE ATTACHMENT
# =========================================================================

def attach_langfuse_scores(trace_id, faithfulness_result, correctness_result, retrieval_hit):
    """
    Attach eval scores to a LangFuse trace so they're queryable in the dashboard.

    Use langfuse.score() with:
      - name="faithfulness", value=faithfulness_result["score"] / 5
      - name="correctness", value=correctness_result["score"] / 5
      - name="retrieval_hit", value=1.0 if retrieval_hit else 0.0

    After attaching, you can filter in LangFuse:
    "Show me all traces where faithfulness < 0.6"

    TODO: Implement in Session 2 homework.
    """
    pass


# =========================================================================
# SESSION 2: SAVE BASELINE
# =========================================================================

def save_baseline(summary_scores, category_breakdown):
    """
    Save current eval scores as baseline_scores.json.
    This becomes the regression anchor — future evals compare against it.

    summary_scores should include: retrieval_hit_rate, avg_faithfulness, avg_correctness
    category_breakdown: per-category correctness scores

    TODO: Implement in Session 2 homework.
    """
    pass


# =========================================================================
# MAIN
# =========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-hard", action="store_true",
                        help="Include hard queries that expose system failures")
    parser.add_argument("--save-baseline", action="store_true",
                        help="Save current scores as baseline_scores.json")
    parser.add_argument("--category", type=str,
                        help="Filter to a specific category (e.g. 'membership')")
    args = parser.parse_args()

    print("Eval harness skeleton loaded.")
    print()
    print("Session 1 functions: check_retrieval_hit, calculate_mrr,")
    print("                     judge_faithfulness, judge_correctness, run_eval")
    print()
    print("Session 2 functions: run_stratified_eval, attach_langfuse_scores, save_baseline")
    print()
    print("Implement Session 1 functions first, then run:")
    print("  python scripts/eval_harness.py")
