"""
Regression Checker — Session 2 Starter

Compares current eval scores against a saved baseline.
Flags any metric that drops more than the threshold.

Functions to implement:
  1. load_baseline() — load baseline_scores.json
  2. load_current() — load eval_results.json (note: scores are under "summary" key)
  3. check_regression() — compare metric by metric, return list of regressions
  4. display_results() — print a clear pass/fail table with deltas

Run: python scripts/check_regression.py
Run with options:
  python scripts/check_regression.py --threshold 3.0
  python scripts/check_regression.py --baseline scripts/baseline_scores.json
"""
import os
import sys
import json
import argparse

from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(__file__)

DEFAULT_BASELINE = os.path.join(SCRIPT_DIR, "baseline_scores.json")
DEFAULT_CURRENT = os.path.join(SCRIPT_DIR, "eval_results.json")
DEFAULT_THRESHOLD = 5.0  # percentage points


# =========================================================================
# FUNCTIONS TO IMPLEMENT IN SESSION 2
# =========================================================================

def load_baseline(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict) and "summary" in data:
        return data["summary"]
    # raw eval_results list — compute summary so any run can be used as baseline
    n = len(data)
    return {
        "n_queries": n,
        "retrieval_hit_rate": sum(1 for r in data if r["retrieval_hit"]) / n,
        "avg_mrr": sum(r["mrr"] for r in data) / n,
        "avg_faithfulness": sum(r["faithfulness"]["score"] for r in data) / n,
        "avg_correctness": sum(r["correctness"]["score"] for r in data) / n,
    }


def load_current(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict) and "summary" in data:
        return data["summary"]
    # raw list of per-query results — compute summary
    n = len(data)
    return {
        "n_queries": n,
        "retrieval_hit_rate": sum(1 for r in data if r["retrieval_hit"]) / n,
        "avg_mrr": sum(r["mrr"] for r in data) / n,
        "avg_faithfulness": sum(r["faithfulness"]["score"] for r in data) / n,
        "avg_correctness": sum(r["correctness"]["score"] for r in data) / n,
    }


def check_regression(current: dict, baseline: dict, threshold: float = DEFAULT_THRESHOLD) -> list:
    # Each metric is normalized to 0-100% before comparing so threshold is always in percentage points.
    # hit_rate is already 0-1 → ×100; faithfulness/correctness are 1-5 → ÷5 ×100
    metrics = [
        ("retrieval_hit_rate", 100),
        ("avg_faithfulness",    20),   # (score / 5) * 100
        ("avg_correctness",     20),
    ]
    results = []
    for metric, scale in metrics:
        b_pct = baseline[metric] * scale
        c_pct = current[metric] * scale
        delta = c_pct - b_pct
        results.append({
            "metric":       metric,
            "baseline":     round(b_pct, 2),
            "current":      round(c_pct, 2),
            "delta":        round(delta, 2),
            "is_regression": delta < -threshold,
        })
    return results


def display_results(regressions: list, threshold: float):
    GREEN = "\033[92m"
    RED   = "\033[91m"
    RESET = "\033[0m"

    print(f"\n{'Metric':<24} {'Baseline':>10} {'Current':>10} {'Delta':>8}  Status")
    print("-" * 65)
    any_regression = False
    for r in regressions:
        status_label = f"{RED}REGRESSION{RESET}" if r["is_regression"] else f"{GREEN}PASS{RESET}"
        delta_str = f"{r['delta']:+.2f}pp"
        print(f"  {r['metric']:<22} {r['baseline']:>9.2f}% {r['current']:>9.2f}% {delta_str:>8}  {status_label}")
        if r["is_regression"]:
            any_regression = True

    print()
    if any_regression:
        print(f"❌  REGRESSION DETECTED  (threshold: {threshold}pp)")
    else:
        print(f"✅  NO REGRESSION  (threshold: {threshold}pp)")


# =========================================================================
# MAIN
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Regression checker for RAG eval")
    parser.add_argument("--baseline", type=str, default=DEFAULT_BASELINE)
    parser.add_argument("--current", type=str, default=DEFAULT_CURRENT)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Regression threshold in percentage points (default: 5.0)")
    args = parser.parse_args()

    baseline = load_baseline(args.baseline)
    current  = load_current(args.current)
    results  = check_regression(current, baseline, args.threshold)
    display_results(results, args.threshold)


if __name__ == "__main__":
    main()
