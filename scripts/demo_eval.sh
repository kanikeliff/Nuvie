#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

python -m aii.evaluation.offline_metrics --k 10 --sample-users 300

echo ""
echo "=== REPORT (md) ==="
cat aii/evaluation/output/evaluation_report.md

echo ""
echo "=== METRICS (json) ==="
cat aii/evaluation/output/evaluation_metrics.json

echo ""
echo "=== COMPARISON ==="
cat aii/evaluation/output/comparison_table.md
