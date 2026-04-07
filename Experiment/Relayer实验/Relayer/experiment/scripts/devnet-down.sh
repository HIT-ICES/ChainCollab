#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME_DIR="$ROOT/src/relayer-node/runtime"

stop_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" || true
      sleep 0.2
      kill -9 "$pid" >/dev/null 2>&1 || true
      echo "stopped pid=$pid"
    fi
    rm -f "$pid_file"
  fi
}

stop_pid_file "$RUNTIME_DIR/anvil-a.pid"
stop_pid_file "$RUNTIME_DIR/anvil-b.pid"

echo "devnet stopped"
