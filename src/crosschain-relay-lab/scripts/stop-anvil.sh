#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/logs"

stop_node() {
  local name="$1"
  local pid_file="$LOG_DIR/${name}.pid"
  if [[ ! -f "$pid_file" ]]; then
    echo "$name not running"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    sleep 0.2
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" || true
    fi
    echo "stopped $name pid=$pid"
  fi
  rm -f "$pid_file"
}

stop_node "anvil-chain-a"
stop_node "anvil-chain-b"
