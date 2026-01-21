#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SCRIPT_DIR="${PROJECT_ROOT}/scripts"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/services.sh"

usage() {
  cat <<'USAGE'
Usage: ./scripts/ctl.sh <command> [service...]

Commands:
  list                List available services
  setup               Install dependencies for services
  start               Start services
  stop                Stop services
  restart             Restart services
  status              Show service status
  clean               Remove local build/dep artifacts

Examples:
  ./scripts/ctl.sh list
  ./scripts/ctl.sh setup front backend
  ./scripts/ctl.sh start            # start all services
  ./scripts/ctl.sh stop agent
USAGE
}

run_action() {
  local action="$1"
  shift
  local targets=("$@")

  if [[ ${#targets[@]} -eq 0 || "${targets[0]}" == "all" ]]; then
    targets=("${SERVICE_NAMES[@]}")
  fi

  local name
  for name in "${targets[@]}"; do
    local svc_script
    svc_script="$(service_script "$name")"
    if [[ -z "$svc_script" || ! -f "$svc_script" ]]; then
      echo "Unknown service: $name"
      continue
    fi
    PROJECT_ROOT="$PROJECT_ROOT" bash "$svc_script" "$action"
  done
}

cmd="${1:-}"
case "$cmd" in
  list)
    list_services
    ;;
  setup|start|stop|restart|status|clean)
    shift
    run_action "$cmd" "$@"
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "Unknown command: $cmd"
    usage
    exit 1
    ;;
esac
