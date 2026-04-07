#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d node_modules ]]; then
  npm install
fi

npm run chain:up
npm run prepare:bpmn:split
npm run compile
npm run deploy:split
npm run experiment:correctness:split-latency

echo "done. reports:"
echo "  - $ROOT/experiment/report/CORRECTNESS_SPLIT_LATENCY_REPORT.md"
echo "  - $ROOT/experiment/report/correctness-split-latency-report.json"
echo "tip: run 'npm run chain:down' when finished."
