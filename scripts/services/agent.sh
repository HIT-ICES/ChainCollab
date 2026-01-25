#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck source=/dev/null
source "${PROJECT_ROOT}/scripts/lib/common.sh"

SERVICE_NAME="agent"
SERVICE_DIR="${PROJECT_ROOT}/src/agent"
APP_DIR="${SERVICE_DIR}/docker-rest-agent"
FRONT_DIR="${SERVICE_DIR}/agent-dashboard"

ensure_dir() {
  if [[ ! -d "$SERVICE_DIR" ]]; then
    echo "Service directory not found: $SERVICE_DIR"
    exit 1
  fi
}

setup() {
  ensure_dir
  if [[ -d "$APP_DIR" ]]; then
    local venv_path="$APP_DIR/venv"
    if [[ ! -d "$venv_path" ]]; then
      python3 -m venv "$venv_path"
    fi
    "$venv_path/bin/pip" install -r "$APP_DIR/requirements.txt"
  fi
  if [[ -d "$FRONT_DIR" ]]; then
    node_install "$FRONT_DIR"
  fi
}

start() {
  ensure_dir
  ensure_runtime_dirs
  AGENT_FRONT_PORT="${AGENT_FRONT_PORT:-5177}" \
  AGENT_LOG_FILE="${LOG_DIR}/agent.log" \
  AGENT_FRONT_LOG="${LOG_DIR}/agent-frontend.log" \
  bash "$SERVICE_DIR/agent_env.sh" start
}

stop() {
  bash "$SERVICE_DIR/agent_env.sh" stop
}

status() {
  bash "$SERVICE_DIR/agent_env.sh" status
}

clean() {
  ensure_dir
  rm -rf "$APP_DIR/venv" "$APP_DIR/__pycache__"
  rm -rf "$FRONT_DIR/node_modules" "$FRONT_DIR/dist" "$FRONT_DIR/.vite"
  rm -f "$SERVICE_DIR/agent.pid" "$SERVICE_DIR/agent-frontend.pid"
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
