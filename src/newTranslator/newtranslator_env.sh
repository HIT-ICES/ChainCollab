export NEWTRANS_ROOT="/home/logres/system/src/newTranslator"
cd "$NEWTRANS_ROOT" || return

export NT_B2C_DIR="$NEWTRANS_ROOT/build/b2c"
export NT_BPMN_DIR="$NEWTRANS_ROOT/build/bpmn"
export NT_BUILD_DIR="$NEWTRANS_ROOT/build/chaincode"
export NT_SOL_DIR="$NEWTRANS_ROOT/build/solidity"
export NT_EXAMPLE="$NT_B2C_DIR/chaincode.b2c"

nt-go-gen() {
  mkdir -p "$NT_B2C_DIR" "$NT_BUILD_DIR"
  textx generate "$NT_EXAMPLE" --target go --overwrite -o "$NT_BUILD_DIR" "$@"
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
  mkdir -p "$NT_B2C_DIR" "$NT_SOL_DIR"
  mkdir -p "$NT_SOL_DIR"
  textx generate "$NT_EXAMPLE" --target solidity --overwrite -o "$NT_SOL_DIR" "$@"
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
  local bpmn_file=${1:-"$NT_BPMN_DIR/amazon.bpmn"}
  local output_file=${2:-"$NT_B2C_DIR/chaincode.b2c"}
  if [ ! -f "$bpmn_file" ]; then
    echo "BPMN file '$bpmn_file' not found. Provide a BPMN file path."
    return 1
  fi
  mkdir -p "$(dirname "$output_file")"
  if command -v python3 >/dev/null 2>&1; then
    python3 "$NEWTRANS_ROOT/DSLGenerator/bpmn_to_dsl.py" "$bpmn_file" -o "$output_file"
  else
    python "$NEWTRANS_ROOT/DSLGenerator/bpmn_to_dsl.py" "$bpmn_file" -o "$output_file"
  fi
}

nt-b2c-view() {
  local b2c_file=${1:-"$NT_B2C_DIR/chaincode.b2c"}
  local dot_file=${2:-"$NT_B2C_DIR/chaincode.dot"}
  local png_file="${dot_file%.dot}.png"
  if [ ! -f "$b2c_file" ]; then
    echo "DSL file '$b2c_file' not found. Provide a .b2c file."
    return 1
  fi
  mkdir -p "$(dirname "$dot_file")"
  /usr/bin/python3.12 - "$b2c_file" "$dot_file" <<'PY'
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

echo "NewTranslator environment loaded."
echo "Commands: nt-go-gen, nt-go-fmt, nt-go-build, nt-go-clean, nt-sol-gen, nt-sol-fmt, nt-sol-build, nt-sol-clean, nt-bpmn-to-b2c, nt-b2c-view"
