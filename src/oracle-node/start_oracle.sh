#!/usr/bin/env bash
set -euo pipefail

# === 配置 ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQ_FILE="${SCRIPT_DIR}/requirements.txt"
EXPORT_PYTHONPATH="${SCRIPT_DIR}"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
BACKEND_PORT="${ORACLE_BACKEND_PORT:-8010}"

echo "[oracle] 一键启动：后端(端口 ${BACKEND_PORT}) + 前端 + 节点"

ensure_venv() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
  fi
  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"
  pip install --upgrade pip >/dev/null
  pip install -r "${REQ_FILE}"
  export PYTHONPATH="${EXPORT_PYTHONPATH}"
}

start_backend() {
  echo "[oracle] 启动 FastAPI 控制平面..."
  uvicorn oracle_node.backend.app:app \
    --app-dir "${SCRIPT_DIR}" \
    --reload \
    --host 0.0.0.0 \
    --port "${BACKEND_PORT}"
}

start_node() {
  echo "[oracle] 启动链下 Oracle 节点..."
  python "${SCRIPT_DIR}/oracle_node/main.py"
}

start_frontend() {
  if [[ ! -d "${FRONTEND_DIR}" ]]; then
    echo "[oracle] 未发现前端目录: ${FRONTEND_DIR}"
    exit 1
  fi
  echo "[oracle] 启动前端 Vite..."
  (cd "${FRONTEND_DIR}" && npm install && npm run dev)
}

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${NODE_PID:-}" ]]; then
    kill "${NODE_PID}" 2>/dev/null || true
  fi
}

main() {
  ensure_venv
  trap cleanup EXIT INT TERM
  start_backend &
  BACKEND_PID=$!
  echo "[oracle] FastAPI 已在 PID ${BACKEND_PID} 后台运行"
  start_frontend &
  FRONTEND_PID=$!
  echo "[oracle] 前端已在 PID ${FRONTEND_PID} 后台运行"
#   start_node &
#   NODE_PID=$!
#   echo "[oracle] 节点已在 PID ${NODE_PID} 后台运行"
  wait
}

main "$@"
