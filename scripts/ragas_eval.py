"""
RAGAS Evaluation — Week 2 / Session 3

Runs the 10 hardest golden queries through RAGAS and compares scores
against our existing LLM-as-judge results.

Metrics collected:
  - faithfulness        : is the answer grounded in retrieved context?
  - answer_relevancy    : does the answer address the question?
  - context_precision   : are retrieved chunks actually relevant?

Side-by-side table: our judge scores vs RAGAS scores.

Run:
  python scripts/ragas_eval.py
  python scripts/ragas_eval.py --mode hybrid
  python scripts/ragas_eval.py --mode dense --out ragas_results_dense.json
"""
import os
import sys
import json
import argparse

from ragas import evaluate, EvaluationDataset, SingleTurnSample
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from ragas.metrics import faithfulness, context_precision, context_recall
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

SCRIPT_DIR = os.path.dirname(__file__)


# =========================================================================
# QUERY SELECTION — 3 hard + 7 worst-performing medium
# =========================================================================

def select_hardest_queries(golden_path, eval_path, n=10):
    """
    Returns the n hardest queries:
      - all 'hard' difficulty entries first
      - remaining slots filled by lowest-correctness 'medium' entries
        from the most recent eval run (eval_results.json)
    """
    with open(golden_path) as f:
        golden = {q["id"]: q for q in json.load(f)}

    hard_queries = [q for q in golden.values() if q.get("difficulty") == "hard"]

    # pull correctness scores from last eval run
    medium_scores = []
    if os.path.exists(eval_path):
        with open(eval_path) as f:
            results = json.load(f)
        for r in results:
            if golden.get(r["id"], {}).get("difficulty") == "medium":
                medium_scores.append((r["correctness"]["score"], golden[r["id"]]))
        medium_scores.sort(key=lambda x: x[0])  # lowest correctness first
    else:
        medium_scores = [(0, q) for q in golden.values() if q.get("difficulty") == "medium"]

    remaining = n - len(hard_queries)
    selected = hard_queries + [q for _, q in medium_scores[:remaining]]
    return selected[:n]


# =========================================================================
# RUN QUERIES THROUGH RAG
# =========================================================================

def run_queries(queries, mode="dense"):
    from rag import ask
    results = []
    for q in queries:
        print(f"  [{q['id']}] {q['query'][:65]}...")
        result = ask(q["query"], mode=mode)
        results.append({
            "id":              q["id"],
            "query":           q["query"],
            "difficulty":      q.get("difficulty"),
            "category":        q.get("category"),
            "expected_source": q.get("expected_source"),
            "expected_answer": q.get("expected_answer"),
            "answer":          result["answer"],
            "context":         result["context"],
            "contexts":        [c["content"] for c in result["retrieved_chunks"]],
            "trace_id":        result["trace_id"],
        })
    return results


# =========================================================================
# RAGAS EVALUATION
# =========================================================================

def run_ragas(results):
    """Build a RAGAS EvaluationDataset and evaluate."""
    samples = [
        SingleTurnSample(
            user_input=r["query"],
            response=r["answer"],
            retrieved_contexts=r["contexts"],
            reference=r["expected_answer"],
        )
        for r in results
    ]
    dataset = EvaluationDataset(samples=samples)

    scores = evaluate(
        dataset,
        metrics=[faithfulness, context_precision, context_recall],
    )
    return scores


# =========================================================================
# COMPARISON TABLE
# =========================================================================

def load_judge_scores(eval_path, query_ids):
    """Pull LLM-as-judge scores from existing eval_results.json for these ids."""
    if not os.path.exists(eval_path):
        return {}
    with open(eval_path) as f:
        data = json.load(f)
    return {
        r["id"]: {
            "judge_faithfulness": r["faithfulness"]["score"] / 5,
            "judge_correctness":  r["correctness"]["score"] / 5,
            "retrieval_hit":      r["retrieval_hit"],
            "mrr":                r["mrr"],
        }
        for r in data if r["id"] in query_ids
    }


def display_comparison(results, ragas_scores, judge_map):
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RESET  = "\033[0m"

    df = ragas_scores.to_pandas()

    print("\n" + "=" * 115)
    print("RAGAS vs LLM-AS-JUDGE COMPARISON")
    print(f"  {'ID':<7} {'Category':<13} {'Diff':<7} "
          f"{'JudgeFaith':>10} {'RagasFaith':>10} "
          f"{'HitRate':>8} {'CtxRecall':>10} "
          f"{'JudgeCorr':>10} {'CtxPrec':>8}")
    print("-" * 100)

    def fmt(v):
        import math
        if v is None:
            return "   N/A"
        if isinstance(v, float) and math.isnan(v):
            return "   N/A"
        return f"{v:6.2f}"

    def diff_flag(a, b, tol=0.15):
        import math
        if a is None or b is None:
            return " "
        if isinstance(a, float) and math.isnan(a):
            return " "
        if isinstance(b, float) and math.isnan(b):
            return " "
        return f"{YELLOW}△{RESET}" if abs(a - b) > tol else f"{GREEN}✓{RESET}"

    for i, r in enumerate(results):
        qid = r["id"]
        row = df.iloc[i]
        j   = judge_map.get(qid, {})

        jf   = j.get("judge_faithfulness")
        jc   = j.get("judge_correctness")
        hit  = j.get("retrieval_hit")
        rf   = row.get("faithfulness")
        rcr  = row.get("context_recall")
        rcp  = row.get("context_precision")

        hit_str = f"{'yes':>7}" if hit else (f"{'no':>7}" if hit is not None else f"{'N/A':>7}")

        print(f"  {qid:<7} {r['category']:<13} {r['difficulty']:<7} "
              f"{fmt(jf):>10} {diff_flag(jf,rf)} {fmt(rf):>10} "
              f"{hit_str} {diff_flag(hit, rcr)} {fmt(rcr):>10} "
              f"{fmt(jc):>10} {fmt(rcp):>8}")

    print("-" * 100)

    def safe_mean(col):
        import math
        vals = [v for v in df[col] if not math.isnan(v)]
        return sum(vals) / len(vals) if vals else float("nan")

    jf_avg  = sum(judge_map[r["id"]]["judge_faithfulness"] for r in results if r["id"] in judge_map) / max(len([r for r in results if r["id"] in judge_map]), 1)
    jc_avg  = sum(judge_map[r["id"]]["judge_correctness"]  for r in results if r["id"] in judge_map) / max(len([r for r in results if r["id"] in judge_map]), 1)
    hit_avg = sum(judge_map[r["id"]]["retrieval_hit"]      for r in results if r["id"] in judge_map) / max(len([r for r in results if r["id"] in judge_map]), 1)

    print(f"  {'AVG':<7} {'':13} {'':7} "
          f"{fmt(jf_avg):>10}   {fmt(safe_mean('faithfulness')):>10} "
          f"{fmt(hit_avg):>8}   {fmt(safe_mean('context_recall')):>10} "
          f"{fmt(jc_avg):>10} {fmt(safe_mean('context_precision')):>8}")
    print("=" * 115)
    print("\nLegend: ✓ = agree within 0.15   △ = diverge >0.15  (HitRate vs CtxRecall comparison)")


# =========================================================================
# MAIN
# =========================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dense", "hybrid"], default="dense")
    parser.add_argument("--out", type=str, default="ragas_results.json",
                        help="Output filename in scripts/ dir")
    args = parser.parse_args()

    golden_path = os.path.join(SCRIPT_DIR, "golden_dataset.json")
    eval_path   = os.path.join(SCRIPT_DIR, "eval_results.json")
    out_path    = os.path.join(SCRIPT_DIR, args.out)

    print(f"\nSelecting 10 hardest queries...")
    queries = select_hardest_queries(golden_path, eval_path)
    for q in queries:
        print(f"  [{q['id']}] [{q['difficulty']}] {q['query'][:65]}")

    print(f"\nRunning queries through RAG (mode={args.mode})...")
    results = run_queries(queries, mode=args.mode)

    print("\nRunning RAGAS evaluation...")
    ragas_scores = run_ragas(results)

    query_ids = {r["id"] for r in results}
    judge_map = load_judge_scores(eval_path, query_ids)

    display_comparison(results, ragas_scores, judge_map)

    # Save full results
    df = ragas_scores.to_pandas()
    output = []
    for i, r in enumerate(results):
        row = df.iloc[i]
        j   = judge_map.get(r["id"], {})
        output.append({
            "id":               r["id"],
            "query":            r["query"],
            "category":         r["category"],
            "difficulty":       r["difficulty"],
            "answer":           r["answer"],
            "expected_answer":  r["expected_answer"],
            "judge_faithfulness": j.get("judge_faithfulness"),
            "judge_correctness":  j.get("judge_correctness"),
            "ragas_faithfulness":     float(row.get("faithfulness", float("nan"))),
            "ragas_context_recall":   float(row.get("context_recall", float("nan"))),
            "ragas_context_precision": float(row.get("context_precision", float("nan"))),
            "retrieval_hit":          j.get("retrieval_hit"),
        })

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
