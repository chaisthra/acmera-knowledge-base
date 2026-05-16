#!/usr/bin/env bash
# Baseline load test: 50 sequential requests, no concurrency
# Usage: bash scripts/load_test_baseline.sh

set -e

ALB_URL="${API_URL:-http://acmera-dev-70623252.ap-south-1.elb.amazonaws.com}"
ENDPOINT="$ALB_URL/query"
PAYLOAD_FILE="/tmp/ab_query_payload.json"
OUTPUT_FILE="scripts/ab_baseline_output.txt"

echo '{"query": "What is the return window?", "mode": "dense"}' > "$PAYLOAD_FILE"

echo "=============================================="
echo "Baseline load test"
echo "Endpoint : $ENDPOINT"
echo "Requests : 50 (c=1, sequential)"
echo "Payload  : $(cat $PAYLOAD_FILE)"
echo "=============================================="
echo ""

# Check ab is installed
if ! command -v ab &>/dev/null; then
  echo "ERROR: Apache Bench not found."
  echo "  macOS : brew install httpd"
  echo "  Ubuntu: sudo apt install apache2-utils"
  exit 1
fi

ab -n 50 -c 1 \
   -p "$PAYLOAD_FILE" \
   -T 'application/json' \
   -s 120 \
   "$ENDPOINT" | tee "$OUTPUT_FILE"

echo ""
echo "=============================================="
echo "Key numbers"
echo "=============================================="
grep -E "Requests per second|Time per request|Transfer rate|^ (50|66|75|80|90|95|98|99|100)" "$OUTPUT_FILE" || true
echo ""
echo "Full output saved to: $OUTPUT_FILE"
