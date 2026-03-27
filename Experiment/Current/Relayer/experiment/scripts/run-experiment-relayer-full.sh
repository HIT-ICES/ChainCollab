#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d node_modules ]]; then
  npm install
fi

TIMING_PROFILE="${RELAYER_TIMING_PROFILE:-default}"
if [[ "$TIMING_PROFILE" == "realistic" ]]; then
  # Use a moderate fixed block time to keep the run realistic without
  # stretching the end-to-end latency too aggressively.
  export ANVIL_BLOCK_TIME="${ANVIL_BLOCK_TIME:-3}"
  export ANVIL_MIXED_MINING="${ANVIL_MIXED_MINING:-0}"
  export RELAYER_FIXED_TASKS_PER_CASE="${RELAYER_FIXED_TASKS_PER_CASE:-0}"
  export RELAYER_RUNS_PER_CASE="${RELAYER_RUNS_PER_CASE:-10}"
else
  export ANVIL_BLOCK_TIME="${ANVIL_BLOCK_TIME:-0}"
  export ANVIL_MIXED_MINING="${ANVIL_MIXED_MINING:-0}"
  export RELAYER_FIXED_TASKS_PER_CASE="${RELAYER_FIXED_TASKS_PER_CASE:-0}"
  export RELAYER_RUNS_PER_CASE="${RELAYER_RUNS_PER_CASE:-0}"
fi
export RELAYER_CONFIRMATIONS="${RELAYER_CONFIRMATIONS:-0}"
export RELAYER_POLL_MS="${RELAYER_POLL_MS:-50}"
export RELAYER_DELIVERY_TIMEOUT_MS="${RELAYER_DELIVERY_TIMEOUT_MS:-180000}"
export RELAYER_DELIVERY_POLL_MS="${RELAYER_DELIVERY_POLL_MS:-20}"
export RELAYER_INLINE="${RELAYER_INLINE:-0}"
export RELAYER_USE_BATCH="${RELAYER_USE_BATCH:-0}"

WORKER_PID=""
cleanup() {
  if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    kill "$WORKER_PID" >/dev/null 2>&1 || true
    wait "$WORKER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

npm run chain:up
npm run prepare:bpmn:split
npm run compile
npm run deploy
npm run deploy:split

if [[ "${RELAYER_INLINE:-0}" != "1" ]]; then
  rm -f "$ROOT/src/relayer-node/runtime/split-relayer-state.json"
  node src/relayer-node/split-worker.js > "$ROOT/src/relayer-node/runtime/split-worker.log" 2>&1 &
  WORKER_PID=$!
  echo "split-worker started pid=$WORKER_PID log=$ROOT/src/relayer-node/runtime/split-worker.log"
else
  echo "RELAYER_INLINE=1, skip split-worker process."
fi

npm run experiment:correctness:split-latency
npm run experiment:latency:full-vs-split
npm run experiment:report

echo "timing profile: $TIMING_PROFILE"
echo "anvil block time: $ANVIL_BLOCK_TIME"
echo "fixed tasks/case: $RELAYER_FIXED_TASKS_PER_CASE"
echo "runs/case: $RELAYER_RUNS_PER_CASE"

echo "done. reports:"
echo "  - $ROOT/experiment/report/RELAYER_UNIFIED_EXPERIMENT_REPORT.md"
echo "  - $ROOT/experiment/report/relayer-unified-report.json"
echo "  - $ROOT/experiment/report/LATENCY_FULL_VS_SPLIT_REPORT.md"
echo "  - $ROOT/experiment/report/latency-full-vs-split-report.json"
echo "  - $ROOT/experiment/report/CORRECTNESS_SPLIT_LATENCY_REPORT.md"
echo "  - (fault recovery temporarily hidden)"
if [[ "${RELAYER_INLINE:-0}" != "1" ]]; then
  echo "worker log:"
  echo "  - $ROOT/src/relayer-node/runtime/split-worker.log"
fi
echo "tip: run 'npm run experiment:fault-recovery' manually if needed."
echo "tip: run 'npm run chain:down' when finished."
