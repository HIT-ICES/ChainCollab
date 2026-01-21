#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck source=/dev/null
source "${PROJECT_ROOT}/scripts/lib/common.sh"

SERVICE_NAME="new_translator"
SERVICE_DIR="${PROJECT_ROOT}/src/newTranslator"
DASH_DIR="${SERVICE_DIR}/dashboard"
VENV_DIR="${NEW_TRANSLATOR_VENV:-$SERVICE_DIR/.venv}"
API_PORT="${NEW_TRANSLATOR_PORT:-9999}"
DASH_PORT="${NEW_TRANSLATOR_DASH_PORT:-5176}"

ensure_dir() {
  if [[ ! -d "$SERVICE_DIR" ]]; then
    echo "Service directory not found: $SERVICE_DIR"
    exit 1
  fi
}

ensure_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi
}

setup() {
  ensure_dir
  ensure_venv
  "$VENV_DIR/bin/pip" install -r "$SERVICE_DIR/requirements.txt"
  "$VENV_DIR/bin/pip" install -e "$SERVICE_DIR/DSL/B2CDSL"
  "$VENV_DIR/bin/pip" install -e "$SERVICE_DIR/CodeGenerator/b2cdsl-go"
  "$VENV_DIR/bin/pip" install -e "$SERVICE_DIR/CodeGenerator/b2cdsl-solidity"
  if [[ -d "$DASH_DIR" ]]; then
    node_install "$DASH_DIR"
  fi
}

start_api() {
  if [[ ! -x "$VENV_DIR/bin/uvicorn" ]]; then
    echo "Virtualenv not found at $VENV_DIR. Run setup first."
    exit 1
  fi
  local cmd
  cmd="PYTHONPATH=\"$PROJECT_ROOT/src\" \"$VENV_DIR/bin/uvicorn\" newTranslator.service.api:app --reload --host 0.0.0.0 --port $API_PORT"
  start_process "${SERVICE_NAME}_api" "$cmd" "$SERVICE_DIR"
}

start_dashboard() {
  if [[ -d "$DASH_DIR" ]]; then
    local cmd
    cmd="$(node_run_cmd "$DASH_DIR" dev --host 0.0.0.0 --port "$DASH_PORT")"
    start_process "${SERVICE_NAME}_dashboard" "$cmd" "$DASH_DIR"
  fi
}

start() {
  start_api
  start_dashboard
}

stop() {
  stop_process "${SERVICE_NAME}_api"
  stop_process "${SERVICE_NAME}_dashboard"
}

status() {
  status_process "${SERVICE_NAME}_api"
  status_process "${SERVICE_NAME}_dashboard"
}

clean() {
  ensure_dir
  rm -rf "$VENV_DIR" "$SERVICE_DIR/__pycache__"
  find "$SERVICE_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
  rm -rf "$DASH_DIR/node_modules" "$DASH_DIR/dist" "$DASH_DIR/.vite"
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
