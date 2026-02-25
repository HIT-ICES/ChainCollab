#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

ANVIL_BIN="${ANVIL_BIN:-$(command -v anvil)}"
if [[ -z "$ANVIL_BIN" ]]; then
  echo "anvil not found"
  exit 1
fi

MNEMONIC="test test test test test test test test test test test junk"

start_node() {
  local name="$1"
  local port="$2"
  local chain_id="$3"
  local pid_file="$LOG_DIR/${name}.pid"
  local log_file="$LOG_DIR/${name}.log"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name already running (pid $(cat "$pid_file"))"
    return
  fi

  nohup "$ANVIL_BIN" \
    --port "$port" \
    --chain-id "$chain_id" \
    --mnemonic "$MNEMONIC" \
    --accounts 20 \
    --balance 100000 \
    > "$log_file" 2>&1 &

  echo $! > "$pid_file"
  echo "started $name on :$port chainId=$chain_id pid=$(cat "$pid_file")"
}

start_node "anvil-chain-a" "8545" "31337"
start_node "anvil-chain-b" "9545" "31338"
