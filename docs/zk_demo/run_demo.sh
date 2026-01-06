#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
PTAU="${BUILD_DIR}/powersOfTau28_hez_final_10.ptau"

mkdir -p "${BUILD_DIR}"

if ! command -v circom >/dev/null 2>&1; then
  echo "circom not found. Please install circom first." >&2
  exit 1
fi

if ! command -v snarkjs >/dev/null 2>&1; then
  echo "snarkjs not found. Please install snarkjs (npm i -g snarkjs)." >&2
  exit 1
fi

echo "[1/6] Compile circuit"
circom "${ROOT_DIR}/circuit.circom" --r1cs --wasm --sym -o "${BUILD_DIR}"

echo "[2/6] Prepare ptau (once)"
if [ ! -f "${PTAU}" ]; then
  snarkjs powersoftau new bn128 10 "${BUILD_DIR}/powersOfTau28_hez_10.ptau" -v
  snarkjs powersoftau contribute "${BUILD_DIR}/powersOfTau28_hez_10.ptau" "${BUILD_DIR}/powersOfTau28_hez_10_contrib.ptau" --name="demo" -v
  snarkjs powersoftau prepare phase2 "${BUILD_DIR}/powersOfTau28_hez_10_contrib.ptau" "${PTAU}" -v
fi

echo "[3/6] Groth16 setup"
snarkjs groth16 setup "${BUILD_DIR}/circuit.r1cs" "${PTAU}" "${BUILD_DIR}/circuit_0000.zkey"
snarkjs zkey contribute "${BUILD_DIR}/circuit_0000.zkey" "${BUILD_DIR}/circuit_final.zkey" --name="demo" -v

echo "[4/6] Generate witness"
node "${BUILD_DIR}/circuit_js/generate_witness.js" "${BUILD_DIR}/circuit_js/circuit.wasm" "${ROOT_DIR}/input.json" "${BUILD_DIR}/witness.wtns"

echo "[5/6] Generate proof"
snarkjs groth16 prove "${BUILD_DIR}/circuit_final.zkey" "${BUILD_DIR}/witness.wtns" "${BUILD_DIR}/proof.json" "${BUILD_DIR}/public.json"

echo "[6/6] Verify proof"
snarkjs zkey export verificationkey "${BUILD_DIR}/circuit_final.zkey" "${BUILD_DIR}/verification_key.json"
snarkjs groth16 verify "${BUILD_DIR}/verification_key.json" "${BUILD_DIR}/public.json" "${BUILD_DIR}/proof.json"

echo "Public output:"
cat "${BUILD_DIR}/public.json"
