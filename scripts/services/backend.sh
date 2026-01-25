#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck source=/dev/null
source "${PROJECT_ROOT}/scripts/lib/common.sh"

SERVICE_NAME="backend"
SERVICE_DIR="${PROJECT_ROOT}/src/backend"
VENV_DIR="${BACKEND_VENV:-$SERVICE_DIR/.venv}"
PORT="${BACKEND_PORT:-8000}"

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
}

start() {
  ensure_dir
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Virtualenv not found at $VENV_DIR. Run setup first."
    exit 1
  fi
  local cmd
  cmd="\"$VENV_DIR/bin/python\" manage.py runserver 0.0.0.0:${PORT}"
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
  rm -rf "$VENV_DIR" "$SERVICE_DIR/__pycache__" "$SERVICE_DIR"/*.pyc
  find "$SERVICE_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
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
