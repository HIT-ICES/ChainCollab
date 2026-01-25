#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

SERVICE_NAMES=(
  bpmn_app
  front
  backend
  agent
  new_translator
)

declare -A SERVICE_DIRS=(
  [bpmn_app]="src/bpmn-chor-app"
  [front]="src/front"
  [backend]="src/backend"
  [agent]="src/agent"
  [new_translator]="src/newTranslator"
)

declare -A SERVICE_SCRIPTS=(
  [bpmn_app]="scripts/services/bpmn_app.sh"
  [front]="scripts/services/front.sh"
  [backend]="scripts/services/backend.sh"
  [agent]="scripts/services/agent.sh"
  [new_translator]="scripts/services/new_translator.sh"
)

service_dir() {
  local name="$1"
  local rel="${SERVICE_DIRS[$name]:-}"
  [[ -n "$rel" ]] && echo "$PROJECT_ROOT/$rel"
}

service_script() {
  local name="$1"
  local rel="${SERVICE_SCRIPTS[$name]:-}"
  [[ -n "$rel" ]] && echo "$PROJECT_ROOT/$rel"
}

list_services() {
  local name
  for name in "${SERVICE_NAMES[@]}"; do
    printf '%-16s %s\n' "$name" "$(service_dir "$name")"
  done
}
