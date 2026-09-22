#!/usr/bin/env bash
set -u

REPO=/home/shenxz-lab/code/ChainCollab
TRANSLATOR="$REPO/src/newTranslator"
PYTHON="$TRANSLATOR/.venv/bin/python"
TEXTX="$TRANSLATOR/.venv/bin/textx"
SOURCE_BPMN="$REPO/Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn"
SOURCE_DMN="$REPO/Experiment/BPMNwithDMNcase/supplyChainPaper.dmn"
ARCHIVE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${1:-$REPO/artifacts/SupplyChainPaper_reproduced_$STAMP}"

if [ -e "$OUT" ]; then
  echo "Refusing to overwrite existing output: $OUT" >&2
  exit 2
fi

mkdir -p "$OUT"/{source_models,pim,fabric/raw,fabric/compile_copy,geth/raw,geth/compiled,generation_contexts,logs,scripts}
cp -p "$SOURCE_BPMN" "$SOURCE_DMN" "$OUT/source_models/"
cp -p "$ARCHIVE_ROOT/scripts/diagnostic.py" "$OUT/scripts/"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$TRANSLATOR"
export PATH="$TRANSLATOR/.venv/bin:/usr/local/go/bin:$PATH"

run_stage() {
  local name="$1"
  shift
  "$@" >"$OUT/logs/$name.stdout" 2>"$OUT/logs/$name.stderr"
  local code=$?
  printf '%s\n' "$code" >"$OUT/logs/$name.exitcode"
  return "$code"
}

run_stage A_bpmn_to_dsl "$PYTHON" "$TRANSLATOR/generator/bpmn_to_dsl.py" "$SOURCE_BPMN" -o "$OUT/pim/SupplyChainPaper.b2c"
run_stage A_parse "$TEXTX" check "$OUT/pim/SupplyChainPaper.b2c"
run_stage B_go_generate "$TEXTX" generate "$OUT/pim/SupplyChainPaper.b2c" --target go --overwrite -o "$OUT/fabric/raw"
run_stage C_solidity_generate "$PYTHON" "$TRANSLATOR/generator/b2c_to_solidity.py" "$OUT/pim/SupplyChainPaper.b2c" -o "$OUT/geth/raw/SupplyChainPaper.sol"
run_stage D_diagnostic "$PYTHON" "$OUT/scripts/diagnostic.py" "$OUT"

cp -a "$OUT/fabric/raw/." "$OUT/fabric/compile_copy/"
GOTOOLCHAIN=auto GOCACHE="$OUT/fabric/build_cache" GOMODCACHE="$OUT/fabric/module_cache" run_stage B_go_compile go build -C "$OUT/fabric/compile_copy" -mod=readonly ./...

SOLC_JS=/home/shenxz-lab/.nvm/versions/node/v18.20.8/lib/node_modules/solc/solc.js
if [ -f "$SOLC_JS" ]; then
  run_stage C_solidity_compile /usr/bin/node "$SOLC_JS" --bin --abi --optimize -o "$OUT/geth/compiled" "$OUT/geth/raw/SupplyChainPaper.sol"
else
  printf '%s\n' "solcjs unavailable" >"$OUT/logs/C_solidity_compile.stderr"
  printf '%s\n' "127" >"$OUT/logs/C_solidity_compile.exitcode"
fi

sha256sum "$OUT/pim/SupplyChainPaper.b2c" >"$OUT/pim/SupplyChainPaper.b2c.sha256"
echo "Reproduction output: $OUT"
