#!/usr/bin/env bash

if [ -n "${BASH_SOURCE[0]:-}" ]; then
  NEWTRANS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [ -n "${ZSH_VERSION:-}" ]; then
  NEWTRANS_ROOT="$(cd "$(dirname "${(%):-%N}")" && pwd)"
else
  NEWTRANS_ROOT="$(cd "$(dirname "$0")" && pwd)"
fi
export NEWTRANS_ROOT
cd "$NEWTRANS_ROOT" || exit 1

export NT_B2C_DIR="$NEWTRANS_ROOT/build/b2c"
export NT_BPMN_DIR="$NEWTRANS_ROOT/build/bpmn"
export NT_BUILD_DIR="$NEWTRANS_ROOT/build/chaincode"
export NT_SOL_DIR="$NEWTRANS_ROOT/build/solidity"
export NT_EXAMPLE="$NT_B2C_DIR/chaincode.b2c"

nt-activate() {
  if [ -f "$NEWTRANS_ROOT/.venv/bin/activate" ]; then
    source "$NEWTRANS_ROOT/.venv/bin/activate"
  fi
}

nt-go-gen() {
  nt-activate
  local b2c_file="${1:-$NT_EXAMPLE}"
  shift || true
  if [ ! -f "$b2c_file" ]; then
    echo "B2C file '$b2c_file' not found. Provide a .b2c file."
    return 1
  fi
  mkdir -p "$NT_B2C_DIR" "$NT_BUILD_DIR"
  textx generate "$b2c_file" --target go --overwrite -o "$NT_BUILD_DIR" "$@"
}

nt-go-fmt() {
  (cd "$NT_BUILD_DIR" && gofmt -w *.go)
}

nt-go-build() {
  (cd "$NT_BUILD_DIR" && GO111MODULE=on go build ./...)
}

nt-go-clean() {
  rm -rf "$NT_BUILD_DIR"
}

nt-sol-gen() {
  nt-activate
  local b2c_file="${1:-$NT_EXAMPLE}"
  shift || true
  if [ ! -f "$b2c_file" ]; then
    echo "B2C file '$b2c_file' not found. Provide a .b2c file."
    return 1
  fi
  mkdir -p "$NT_B2C_DIR" "$NT_SOL_DIR"
  textx generate "$b2c_file" --target solidity --overwrite -o "$NT_SOL_DIR" "$@"
}

nt-sol-fmt() {
  if ! command -v solhint >/dev/null 2>&1; then
    echo "solhint not found; please install it or run formatting manually."
    return 1
  fi
  local config="$NEWTRANS_ROOT/.solhint.json"
  if [ ! -f "$config" ]; then
    echo "No .solhint.json found in $NEWTRANS_ROOT; skipping solhint."
    return 1
  fi
  (
    cd "$NT_SOL_DIR" || exit 1
    for f in *.sol; do
      [ -f "$f" ] || continue
      solhint --config "$config" "$f"
    done
  )
}

nt-sol-clean() {
  rm -rf "$NT_SOL_DIR"
}

nt-sol-build() {
  if ! command -v solc >/dev/null 2>&1; then
    echo "solc compiler not found. Please install solc to perform Solidity builds."
    return 1
  fi
  if [ ! -d "$NT_SOL_DIR" ]; then
    echo "No Solidity build directory found. Run nt-sol-gen first."
    return 1
  fi
  local artifacts="$NT_SOL_DIR/artifacts"
  mkdir -p "$artifacts"
  (
    cd "$NT_SOL_DIR" || exit 1
    shopt -s nullglob
    local sources=( *.sol )
    if [ ${#sources[@]} -eq 0 ]; then
      echo "No Solidity sources to compile in $NT_SOL_DIR"
      exit 1
    fi
    solc --bin --abi --metadata --optimize --overwrite -o "$artifacts" "${sources[@]}"
  )
}

nt-bpmn-to-b2c() {
  nt-activate
  local bpmn_file="${1:-}"
  shift || true
  local output_file="$NT_B2C_DIR/chaincode.b2c"

  if [ -z "$bpmn_file" ]; then
    local candidates=("$NT_BPMN_DIR"/*.bpmn)
    if [ ${#candidates[@]} -eq 0 ]; then
      echo "No BPMN files found under $NT_BPMN_DIR. Provide a BPMN file path."
      return 1
    fi
    echo "Select a BPMN source:"
    select choice in "${candidates[@]}" "Cancel"; do
      if [ "$choice" = "Cancel" ] || [ -z "$choice" ]; then
        echo "Cancelled."
        return 1
      fi
      bpmn_file="$choice"
      break
    done
  fi

  if [ $# -gt 0 ] && [[ "${1:-}" != --* ]]; then
    output_file="$1"
    shift || true
  fi

  if [ ! -f "$bpmn_file" ]; then
    echo "BPMN file '$bpmn_file' not found. Provide a valid path."
    return 1
  fi

  mkdir -p "$(dirname "$output_file")"
  if command -v python3 >/dev/null 2>&1; then
    python3 -m generator.bpmn_to_dsl "$bpmn_file" -o "$output_file" "$@"
  else
    python -m generator.bpmn_to_dsl "$bpmn_file" -o "$output_file" "$@"
  fi
}

nt-b2c-view() {
  nt-activate
  local b2c_file=${1:-"$NT_B2C_DIR/chaincode.b2c"}
  local dot_file=${2:-"$NT_B2C_DIR/chaincode.dot"}
  local png_file="${dot_file%.dot}.png"
  if [ ! -f "$b2c_file" ]; then
    echo "DSL file '$b2c_file' not found. Provide a .b2c file."
    return 1
  fi
  mkdir -p "$(dirname "$dot_file")"
  python3 - "$b2c_file" "$dot_file" <<'PY'
import sys
from textx import metamodel_from_file
from textx.export import model_export

b2c_path, dot_path = sys.argv[1], sys.argv[2]
mm = metamodel_from_file("DSL/B2CDSL/b2cdsl/b2c.tx")
model = mm.model_from_file(b2c_path)
model_export(model, dot_path)
PY
  echo "DOT graph written to $dot_file"
  if command -v dot >/dev/null 2>&1; then
    dot -Tpng "$dot_file" -o "$png_file"
    echo "PNG visualization written to $png_file"
  else
    echo "Install Graphviz 'dot' to produce PNG output (e.g. dot -Tpng \"$dot_file\" -o \"$png_file\")."
  fi
}

nt-bootstrap() {
  if [ -f "$NEWTRANS_ROOT/.venv/bin/activate" ]; then
    source "$NEWTRANS_ROOT/.venv/bin/activate"
  else
    python3 -m venv "$NEWTRANS_ROOT/.venv"
    source "$NEWTRANS_ROOT/.venv/bin/activate"
  fi
  python3 -m pip install --upgrade pip
  python3 -m pip install -r "$NEWTRANS_ROOT/requirements.txt"
  python3 -m pip install -e "$NEWTRANS_ROOT/DSL/B2CDSL"
  python3 -m pip install -e "$NEWTRANS_ROOT/CodeGenerator/b2cdsl-go"
  python3 -m pip install -e "$NEWTRANS_ROOT/CodeGenerator/b2cdsl-solidity"
  echo "Bootstrap complete."
}

nt-clean-env() {
  if [ -d "$NEWTRANS_ROOT/.venv" ]; then
    rm -rf "$NEWTRANS_ROOT/.venv"
    echo "Removed $NEWTRANS_ROOT/.venv"
  else
    echo "No .venv found under $NEWTRANS_ROOT"
  fi
}

show_help() {
  cat <<'EOF'
NewTranslator helper (no source required)

Usage:
  ./newtranslator_env.sh <command> [args...]

Commands:
  bootstrap         Create venv and install deps
  clean-env         Remove .venv
  go-gen            Generate Go chaincode from .b2c
  go-fmt            Run gofmt in build/chaincode
  go-build          Go build in build/chaincode
  go-clean          Remove build/chaincode
  sol-gen           Generate Solidity contracts from .b2c
  sol-fmt           Run solhint on Solidity output
  sol-build         Compile Solidity output with solc
  sol-clean         Remove build/solidity
  bpmn-to-b2c        Convert .bpmn to .b2c
  b2c-view          Render .b2c to dot/png
  help              Show this help

Examples:
  ./newtranslator_env.sh bpmn-to-b2c ./build/bpmn/YourFlow.bpmn
  ./newtranslator_env.sh go-gen ./build/b2c/chaincode.b2c
EOF
}

command="${1:-help}"
shift || true

case "$command" in
  bootstrap) nt-bootstrap "$@" ;;
  clean-env) nt-clean-env "$@" ;;
  go-gen) nt-go-gen "$@" ;;
  go-fmt) nt-go-fmt "$@" ;;
  go-build) nt-go-build "$@" ;;
  go-clean) nt-go-clean "$@" ;;
  sol-gen) nt-sol-gen "$@" ;;
  sol-fmt) nt-sol-fmt "$@" ;;
  sol-build) nt-sol-build "$@" ;;
  sol-clean) nt-sol-clean "$@" ;;
  bpmn-to-b2c) nt-bpmn-to-b2c "$@" ;;
  b2c-view) nt-b2c-view "$@" ;;
  help|-h|--help) show_help ;;
  *)
    echo "Unknown command: $command"
    show_help
    exit 1
    ;;
esac
