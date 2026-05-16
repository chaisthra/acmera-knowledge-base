#!/usr/bin/env bash
# Concurrency ramp load test — finds latency inflection point
# Usage: bash scripts/load_test_concurrency.sh
# Requires: ab (brew install httpd)

set -e

ALB_URL="${API_URL:-http://acmera-dev-70623252.ap-south-1.elb.amazonaws.com}"
ENDPOINT="$ALB_URL/query"
PAYLOAD_FILE="/tmp/ab_query_payload.json"
RESULTS_DIR="scripts/load_test_results"

mkdir -p "$RESULTS_DIR"
echo '{"query": "What is the return window?", "mode": "dense"}' > "$PAYLOAD_FILE"

if ! command -v ab &>/dev/null; then
  echo "ERROR: Apache Bench not found. Run: brew install httpd"
  exit 1
fi

echo "=============================================="
echo "Concurrency ramp load test"
echo "Endpoint : $ENDPOINT"
echo "=============================================="
echo ""

# concurrency | total_requests
PROFILES=(
  "1 50"
  "5 100"
  "20 200"
  "50 500"
  "100 1000"
)

SUMMARY_FILE="$RESULTS_DIR/summary_table.txt"
printf "%-12s %-12s %-10s %-10s %-10s\n" "Concurrency" "Req/sec" "p50 (ms)" "p95 (ms)" "Failed" > "$SUMMARY_FILE"
printf "%-12s %-12s %-10s %-10s %-10s\n" "-----------" "-------" "--------" "--------" "------" >> "$SUMMARY_FILE"

for profile in "${PROFILES[@]}"; do
  c=$(echo $profile | awk '{print $1}')
  n=$(echo $profile | awk '{print $2}')
  out="$RESULTS_DIR/ab_c${c}_n${n}.txt"

  echo "----------------------------------------------"
  echo "Running: c=$c  n=$n"
  echo "----------------------------------------------"

  ab -n "$n" -c "$c" \
     -p "$PAYLOAD_FILE" \
     -T 'application/json' \
     -s 120 \
     "$ENDPOINT" 2>&1 | tee "$out"

  # Extract key metrics
  rps=$(grep "Requests per second" "$out" | awk '{print $4}')
  p50=$(grep "^ *50%" "$out" | awk '{print $2}')
  p95=$(grep "^ *95%" "$out" | awk '{print $2}')
  failed=$(grep "Failed requests" "$out" | awk '{print $3}')

  printf "%-12s %-12s %-10s %-10s %-10s\n" "c=$c" "$rps" "$p50" "$p95" "$failed" >> "$SUMMARY_FILE"

  echo ""
  echo "  -> req/sec=$rps  p50=${p50}ms  p95=${p95}ms  failed=$failed"
  echo ""

  # Brief pause between profiles to let the service recover
  if [ "$c" -lt 100 ]; then
    echo "Waiting 10s before next profile..."
    sleep 10
  fi
done

echo "=============================================="
echo "SUMMARY TABLE"
echo "=============================================="
cat "$SUMMARY_FILE"
echo ""
echo "Full per-profile outputs saved to: $RESULTS_DIR/"
