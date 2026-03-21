#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d node_modules ]]; then
  npm install
fi

npm run chain:up
npm run compile
npm run deploy
npm run prepare:bpmn:split
npm run experiment:correctness:scaled
npm run experiment:fault-recovery

echo "done. reports:"
echo "  - $ROOT/experiment/report/CORRECTNESS_SCALED_REPORT.md"
echo "  - $ROOT/experiment/report/FAULT_RECOVERY_REPORT.md"
echo "  - $ROOT/experiment/report/bpmn-split-cases.json"
echo "tip: run 'npm run chain:down' when finished."
