#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

npm install
npm run anvil:up
npm run deploy

echo "crosschain-relay-lab up complete"
echo "next: npm run relay   # start relayer server"
echo "or:   npm run experiment"
