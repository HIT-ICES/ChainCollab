#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
RUN_DIR="${PROJECT_ROOT}/var/run"
LOG_DIR="${PROJECT_ROOT}/var/log"

ensure_runtime_dirs() {
  mkdir -p "$RUN_DIR" "$LOG_DIR"
}

pid_file() {
  echo "${RUN_DIR}/$1.pid"
}

log_file() {
  echo "${LOG_DIR}/$1.log"
}

is_running() {
  local pid_file_path="$1"
  local pid=""
  pid="$(cat "$pid_file_path" 2>/dev/null || true)"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

start_process() {
  local name="$1"
  local cmd="$2"
  local workdir="$3"
  ensure_runtime_dirs
  local pid_path
  local log_path
  pid_path="$(pid_file "$name")"
  log_path="$(log_file "$name")"

  if is_running "$pid_path"; then
    echo "$name already running (PID $(cat "$pid_path"))."
    return 0
  fi

  (
    cd "$workdir"
    nohup bash -lc "$cmd" >>"$log_path" 2>&1 &
    echo $! >"$pid_path"
  )

  echo "Started $name (PID $(cat "$pid_path")). Logs: $log_path"
}

stop_process() {
  local name="$1"
  local pid_path
  pid_path="$(pid_file "$name")"

  if [[ ! -f "$pid_path" ]]; then
    echo "No PID file for $name."
    return 0
  fi

  local pid
  pid="$(cat "$pid_path")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "Stopping $name (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    echo "$name stopped."
  else
    echo "$name process $pid not running."
  fi

  rm -f "$pid_path"
}

status_process() {
  local name="$1"
  local pid_path
  pid_path="$(pid_file "$name")"

  if is_running "$pid_path"; then
    echo "$name running (PID $(cat "$pid_path"))."
  else
    echo "$name not running."
  fi
}

pick_node_manager() {
  local dir="$1"
  if [[ -n "${NODE_PKG_MANAGER:-}" ]]; then
    echo "$NODE_PKG_MANAGER"
    return 0
  fi
  if [[ -f "$dir/pnpm-lock.yaml" ]] && command -v pnpm >/dev/null 2>&1; then
    echo "pnpm"
    return 0
  fi
  if [[ -f "$dir/yarn.lock" ]] && command -v yarn >/dev/null 2>&1; then
    echo "yarn"
    return 0
  fi
  echo "npm"
}

node_install() {
  local dir="$1"
  local mgr
  mgr="$(pick_node_manager "$dir")"
  case "$mgr" in
    pnpm)
      (cd "$dir" && pnpm install)
      ;;
    yarn)
      (cd "$dir" && yarn install)
      ;;
    *)
      (cd "$dir" && npm install)
      ;;
  esac
}

node_run_cmd() {
  local dir="$1"
  local script="$2"
  shift 2
  local mgr
  mgr="$(pick_node_manager "$dir")"
  local args=()
  local arg
  for arg in "$@"; do
    args+=("$(printf '%q' "$arg")")
  done
  local arg_str="${args[*]}"
  case "$mgr" in
    pnpm)
      echo "pnpm run $script -- $arg_str"
      ;;
    yarn)
      echo "yarn $script $arg_str"
      ;;
    *)
      echo "npm run $script -- $arg_str"
      ;;
  esac
}
