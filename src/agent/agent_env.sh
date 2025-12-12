#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/docker-rest-agent"
VENV_PATH="${AGENT_VENV:-$APP_DIR/venv}"
PID_FILE="$ROOT_DIR/agent.pid"
LOG_FILE="${AGENT_LOG_FILE:-$ROOT_DIR/agent.log}"
FRONT_DIR="$ROOT_DIR/agent-dashboard"
FRONT_PID_FILE="$ROOT_DIR/agent-frontend.pid"
FRONT_PORT="${AGENT_FRONT_PORT:-5173}"
FRONT_LOG_FILE="${AGENT_FRONT_LOG:-$ROOT_DIR/agent-frontend.log}"

export DOCKER_URL="${DOCKER_URL:-unix:///var/run/docker.sock}"
export STORAGE_PATH="${STORAGE_PATH:-$APP_DIR/storage}"
export FABRIC_NETWORK_NAME="${FABRIC_NETWORK_NAME:-cello-net}"

agent_activate() {
  if [[ -f "$VENV_PATH/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$VENV_PATH/bin/activate"
    echo "Using virtualenv: $VENV_PATH"
  else
    echo "No virtualenv found at $VENV_PATH. Continuing with system interpreter."
  fi
}

agent_start() {
  if [[ -f "$PID_FILE" ]]; then
    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Agent already running (PID $(cat "$PID_FILE"))."
      return 0
    else
      rm -f "$PID_FILE"
    fi
  fi

  cd "$APP_DIR"
  agent_activate

  echo "Starting docker-rest-agent via gunicorn..."
  nohup gunicorn --bind 0.0.0.0:5001 server:app >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  echo "Agent started (PID $(cat "$PID_FILE")). Logs: $LOG_FILE"
}

agent_front_start() {
  if [[ ! -d "$FRONT_DIR" ]]; then
    echo "Front-end directory not found: $FRONT_DIR"
    return 1
  fi
  if [[ -f "$FRONT_PID_FILE" ]] && kill -0 "$(cat "$FRONT_PID_FILE")" 2>/dev/null; then
    echo "Front-end already running (PID $(cat "$FRONT_PID_FILE"))."
    return 0
  fi
  (
    cd "$FRONT_DIR"
    echo "Starting front-end (npm run dev -- --host 0.0.0.0 --port $FRONT_PORT)"
    nohup npm run dev -- --host 0.0.0.0 --port "$FRONT_PORT" >>"$FRONT_LOG_FILE" 2>&1 &
    echo $! >"$FRONT_PID_FILE"
  )
  echo "Front-end started (PID $(cat "$FRONT_PID_FILE")). Logs: $FRONT_LOG_FILE"
}

agent_front_stop() {
  if [[ ! -f "$FRONT_PID_FILE" ]]; then
    echo "No front-end PID file found."
    return 0
  fi
  PID="$(cat "$FRONT_PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping front-end (PID $PID)..."
    kill "$PID"
    wait "$PID" 2>/dev/null || true
    echo "Front-end stopped."
  else
    echo "Front-end process $PID not running."
  fi
  rm -f "$FRONT_PID_FILE"
}

agent_front_status() {
  if [[ -f "$FRONT_PID_FILE" ]] && kill -0 "$(cat "$FRONT_PID_FILE")" 2>/dev/null; then
    echo "Front-end running (PID $(cat "$FRONT_PID_FILE"))."
  else
    echo "Front-end not running."
  fi
}

agent_stop() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "No PID file found; agent may not be running."
    return 0
  fi
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping agent (PID $PID)..."
    kill "$PID"
    wait "$PID" 2>/dev/null || true
    echo "Agent stopped."
  else
    echo "Process $PID not running."
  fi
  rm -f "$PID_FILE"
}

agent_status() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Agent running (PID $(cat "$PID_FILE"))."
  else
    echo "Agent not running."
  fi
  agent_front_status
}

agent_restart() {
  agent_stop
  agent_front_stop
  agent_start
  agent_front_start
}

agent_usage() {
  cat <<EOF
Available functions:
  agent_activate  - source virtualenv (if present)
  agent_start     - start gunicorn backend
  agent_stop      - stop backend
  agent_restart   - restart backend
  agent_status    - show backend status
  agent_front_start - start React front-end dev server
  agent_front_stop  - stop front-end
  agent_front_status- show front-end status

Environment variables you can override before sourcing:
  DOCKER_URL, STORAGE_PATH, FABRIC_NETWORK_NAME, AGENT_VENV, AGENT_LOG_FILE, AGENT_FRONT_PORT, AGENT_FRONT_LOG
EOF
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  case "${1:-start}" in
    start)
      agent_start
      agent_front_start
      ;;
    stop)
      agent_stop
      agent_front_stop
      ;;
    status)
      agent_status
      ;;
    restart)
      agent_restart
      ;;
    *)
      echo "Usage: $0 {start|stop|restart|status}"
      exit 1
      ;;
  esac
else
  echo "Agent environment loaded. Run agent_usage for available helper functions."
fi
