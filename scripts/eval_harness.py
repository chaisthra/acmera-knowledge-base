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
    prompt = f"""You are an evaluation judge. Score whether the generated answer correctly addresses the question compared to the expected answer.

Rubric:
- Score 5: Generated answer is fully correct and covers all key points of the expected answer.
- Score 4: Mostly correct with minor omissions or imprecise details.
- Score 3: Partially correct — captures some key points but misses others.
- Score 2: Mostly incorrect or significantly incomplete.
- Score 1: Wrong or completely unrelated to the expected answer.

Question: {query}

Expected answer: {expected_answer}

Generated answer: {answer}

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
    from rag import ask

    dataset = load_golden_dataset()
    if not dataset:
        return

    if not include_hard:
        dataset = [q for q in dataset if q.get("difficulty") != "hard"]

    print(f"\nRunning eval on {len(dataset)} queries...\n")

    results = []
    for q in dataset:
        print(f"  [{q['id']}] {q['query'][:60]}...")

        rag_result = ask(q["query"])

        hit = check_retrieval_hit(rag_result["retrieved_chunks"], q["expected_source"])
        mrr = calculate_mrr(rag_result["retrieved_chunks"], q["expected_source"])
        faith = judge_faithfulness(q["query"], rag_result["answer"], rag_result["context"])
        correct = judge_correctness(q["query"], rag_result["answer"], q["expected_answer"])

        results.append({
            "id": q["id"],
            "query": q["query"],
            "category": q.get("category", "unknown"),
            "difficulty": q.get("difficulty", "easy"),
            "expected_source": q["expected_source"],
            "expected_answer": q["expected_answer"],
            "answer": rag_result["answer"],
            "trace_id": rag_result["trace_id"],
            "retrieval_hit": hit,
            "mrr": mrr,
            "faithfulness": faith,
            "correctness": correct,
            "elapsed_seconds": rag_result["elapsed_seconds"],
        })

        print(f"         hit={hit}  mrr={mrr:.2f}  faith={faith['score']}  correct={correct['score']}")

    # --- Scorecard ---
    n = len(results)
    hit_rate = sum(1 for r in results if r["retrieval_hit"]) / n
    avg_mrr = sum(r["mrr"] for r in results) / n
    avg_faith = sum(r["faithfulness"]["score"] for r in results) / n
    avg_correct = sum(r["correctness"]["score"] for r in results) / n

    print("\n" + "=" * 50)
    print("EVAL SCORECARD")
    print("=" * 50)
    print(f"  Queries evaluated : {n}")
    print(f"  Retrieval hit rate: {hit_rate:.0%}")
    print(f"  Mean Reciprocal Rank (MRR): {avg_mrr:.2f}")
    print(f"  Avg faithfulness  : {avg_faith:.2f} / 5")
    print(f"  Avg correctness   : {avg_correct:.2f} / 5")
    print("=" * 50)

    # --- Save results ---
    out_path = os.path.join(SCRIPT_DIR, "eval_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    return results


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
    from collections import defaultdict

    # --- By category ---
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)

    print("\n" + "=" * 70)
    print("BREAKDOWN BY CATEGORY")
    print(f"{'Category':<16} {'N':>3}  {'Hit%':>6}  {'MRR':>5}  {'Faith':>6}  {'Correct':>7}")
    print("-" * 70)

    category_breakdown = {}
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        n = len(rows)
        hit = sum(1 for r in rows if r["retrieval_hit"]) / n
        mrr = sum(r["mrr"] for r in rows) / n
        faith = sum(r["faithfulness"]["score"] for r in rows) / n
        correct = sum(r["correctness"]["score"] for r in rows) / n
        print(f"  {cat:<14} {n:>3}  {hit:>5.0%}  {mrr:>5.2f}  {faith:>6.2f}  {correct:>7.2f}")
        category_breakdown[cat] = {
            "n": n,
            "hit_rate": round(hit, 4),
            "avg_mrr": round(mrr, 4),
            "avg_faithfulness": round(faith, 4),
            "avg_correctness": round(correct, 4),
        }

    # --- By difficulty ---
    by_diff = defaultdict(list)
    for r in results:
        by_diff[r["difficulty"]].append(r)

    print()
    print("BREAKDOWN BY DIFFICULTY")
    print(f"{'Difficulty':<12} {'N':>3}  {'Hit%':>6}  {'Correct':>7}")
    print("-" * 40)
    for diff in ["easy", "medium", "hard"]:
        if diff not in by_diff:
            continue
        rows = by_diff[diff]
        n = len(rows)
        hit = sum(1 for r in rows if r["retrieval_hit"]) / n
        correct = sum(r["correctness"]["score"] for r in rows) / n
        print(f"  {diff:<10} {n:>3}  {hit:>5.0%}  {correct:>7.2f}")

    print("=" * 70)

    # --- Worst 3 categories by correctness ---
    ranked = sorted(category_breakdown.items(), key=lambda x: x[1]["avg_correctness"])
    print("\nWorst 3 categories by correctness:")
    for i, (cat, scores) in enumerate(ranked[:3], 1):
        print(f"  {i}. {cat}: {scores['avg_correctness']:.2f}/5 correctness, {scores['hit_rate']:.0%} hit rate")

    return category_breakdown


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
    import datetime
    baseline = {
        "saved_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": summary_scores,
        "categories": category_breakdown,
    }
    path = os.path.join(SCRIPT_DIR, "baseline_scores.json")
    with open(path, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"\nBaseline saved to {path}")


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

    results = run_eval(include_hard=args.include_hard)

    if not results:
        sys.exit(1)

    category_breakdown = run_stratified_eval(results)

    if args.save_baseline:
        n = len(results)
        summary_scores = {
            "n_queries": n,
            "retrieval_hit_rate": round(sum(1 for r in results if r["retrieval_hit"]) / n, 4),
            "avg_mrr": round(sum(r["mrr"] for r in results) / n, 4),
            "avg_faithfulness": round(sum(r["faithfulness"]["score"] for r in results) / n, 4),
            "avg_correctness": round(sum(r["correctness"]["score"] for r in results) / n, 4),
        }
        save_baseline(summary_scores, category_breakdown)
