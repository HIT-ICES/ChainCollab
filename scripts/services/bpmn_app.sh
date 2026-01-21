#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck source=/dev/null
source "${PROJECT_ROOT}/scripts/lib/common.sh"

SERVICE_NAME="bpmn_app"
SERVICE_DIR="${PROJECT_ROOT}/src/bpmn-chor-app"
HOST="${BPMN_APP_HOST:-0.0.0.0}"
PORT="${BPMN_APP_PORT:-5174}"

ensure_dir() {
  if [[ ! -d "$SERVICE_DIR" ]]; then
    echo "Service directory not found: $SERVICE_DIR"
    exit 1
  fi
}

setup() {
  ensure_dir
  node_install "$SERVICE_DIR"
}

start() {
  ensure_dir
  local cmd
  cmd="$(node_run_cmd "$SERVICE_DIR" dev --host "$HOST" --port "$PORT")"
  start_process "$SERVICE_NAME" "$cmd" "$SERVICE_DIR"
}

stop() {
  stop_process "$SERVICE_NAME"
}

status() {
  status_process "$SERVICE_NAME"
}

clean() {
  ensure_dir
  rm -rf "$SERVICE_DIR/node_modules" "$SERVICE_DIR/dist" "$SERVICE_DIR/.vite"
  echo "Cleaned $SERVICE_NAME artifacts."
}

restart() {
  stop
  start
}

case "${1:-}" in
  setup) setup ;;
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  clean) clean ;;
  *)
    echo "Usage: $0 {setup|start|stop|restart|status|clean}"
    exit 1
    ;;
esac
