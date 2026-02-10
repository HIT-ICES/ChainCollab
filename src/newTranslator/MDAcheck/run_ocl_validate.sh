#!/usr/bin/env bash
set -euo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$here/.." && pwd)"

ecore="${1:-$here/b2c.ecore}"
ocl="${2:-$here/check.ocl}"
xmi="${3:-$here/chaincode.xmi}"
b2c="${4:-$root/build/b2c/chaincode.b2c}"

echo "[1/3] Export Ecore"
"$root/.venv/bin/python" "$here/export_b2c_ecore.py" --out "$ecore" >/dev/null

echo "[2/3] Convert .b2c -> .xmi"
"$root/.venv/bin/python" "$here/b2c_to_xmi.py" --in "$b2c" --out "$xmi" >/dev/null

echo "[3/3] Validate XMI with Eclipse OCL (Complete OCL)"
#
# Note: Eclipse OCL (Pivot/CompleteOCL) is distributed primarily as Eclipse bundles (p2),
# not Maven Central artifacts. We therefore validate using Tycho+p2.
#
mvn -q -f "$here/ocl-runner-tycho/pom.xml" -U \
  -Dtycho.disableP2Mirrors=true \
  -Decore="$ecore" -Docl="$ocl" -Dxmi="$xmi" \
  integration-test
