#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_DIR="$ROOT/src/relayer-node/runtime"
mkdir -p "$RUNTIME_DIR"

A_PID_FILE="$RUNTIME_DIR/anvil-a.pid"
B_PID_FILE="$RUNTIME_DIR/anvil-b.pid"
A_LOG="$RUNTIME_DIR/anvil-a.log"
B_LOG="$RUNTIME_DIR/anvil-b.log"

MNEMONIC="test test test test test test test test test test test junk"
ANVIL_BLOCK_TIME="${ANVIL_BLOCK_TIME:-0}"
ANVIL_MIXED_MINING="${ANVIL_MIXED_MINING:-0}"
ANVIL_CODE_SIZE_LIMIT="${ANVIL_CODE_SIZE_LIMIT:-1000000}"
ANVIL_GAS_LIMIT="${ANVIL_GAS_LIMIT:-100000000}"

start_anvil() {
  local name="$1"
  local port="$2"
  local chain_id="$3"
  local pid_file="$4"
  local log_file="$5"

  if [[ -f "$pid_file" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"
    if kill -0 "$existing_pid" >/dev/null 2>&1; then
      echo "[$name] already running pid=$existing_pid"
      return
    fi
  fi

  local cmd=(
    anvil
    --host 127.0.0.1
    --port "$port"
    --chain-id "$chain_id"
    --accounts 10
    --mnemonic "$MNEMONIC"
    --code-size-limit "$ANVIL_CODE_SIZE_LIMIT"
    --gas-limit "$ANVIL_GAS_LIMIT"
  )
  if [[ "$ANVIL_BLOCK_TIME" != "0" ]]; then
    cmd+=(--block-time "$ANVIL_BLOCK_TIME")
    if [[ "$ANVIL_MIXED_MINING" == "1" ]]; then
      cmd+=(--mixed-mining)
    fi
  fi

  nohup "${cmd[@]}" >"$log_file" 2>&1 &
  local pid=$!
  echo "$pid" > "$pid_file"
  echo "[$name] started pid=$pid port=$port chain_id=$chain_id"
}

wait_rpc() {
  local url="$1"
  local retry=0
  until curl -sS -H 'Content-Type: application/json' \
      --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' \
      "$url" >/dev/null 2>&1; do
    retry=$((retry + 1))
    if [[ "$retry" -ge 30 ]]; then
      echo "rpc not ready: $url"
      exit 1
    fi
    sleep 0.5
  done
}

start_anvil "chainA" 8545 31337 "$A_PID_FILE" "$A_LOG"
start_anvil "chainB" 9545 31338 "$B_PID_FILE" "$B_LOG"

wait_rpc "http://127.0.0.1:8545"
wait_rpc "http://127.0.0.1:9545"

cat > "$RUNTIME_DIR/devnet.json" <<JSON
{
  "generatedAt": "$(date -Iseconds)",
  "mnemonic": "$MNEMONIC",
  "deployerIndex": 0,
  "relayerIndex": 1,
  "source": {
    "name": "chainA",
    "rpcUrl": "http://127.0.0.1:8545",
    "chainId": 31337
  },
  "target": {
    "name": "chainB",
    "rpcUrl": "http://127.0.0.1:9545",
    "chainId": 31338
  }
}
JSON

echo "devnet ready: $RUNTIME_DIR/devnet.json"
if [[ "$ANVIL_BLOCK_TIME" != "0" ]]; then
  echo "anvil block-time(s): $ANVIL_BLOCK_TIME"
  if [[ "$ANVIL_MIXED_MINING" == "1" ]]; then
    echo "anvil mining mode: mixed-mining"
  fi
fi
