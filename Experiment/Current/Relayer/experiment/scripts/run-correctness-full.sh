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
npm run experiment:correctness

echo "done. reports:"
echo "  - $ROOT/experiment/report/correctness-report.json"
echo "  - $ROOT/experiment/report/CORRECTNESS_REPORT.md"
echo "tip: run 'npm run chain:down' when finished."
