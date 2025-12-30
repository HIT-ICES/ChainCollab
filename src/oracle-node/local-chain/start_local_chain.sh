#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/local-chain"
PORT="${CHAIN_PORT:-8545}"
HOST="${CHAIN_HOST:-0.0.0.0}"
RPC_HOST="${CHAIN_RPC_HOST:-127.0.0.1}"
MNEMONIC_FILE="${OUT_DIR}/mnemonic.txt"
DEFAULT_MNEMONIC="test test test test test test test test test test test junk"
if [ -f "${MNEMONIC_FILE}" ]; then
  MNEMONIC="$(cat "${MNEMONIC_FILE}")"
else
  MNEMONIC="${CHAIN_MNEMONIC:-${DEFAULT_MNEMONIC}}"
fi

mkdir -p "${OUT_DIR}"
echo "${MNEMONIC}" > "${MNEMONIC_FILE}"

NODE_LOG="${OUT_DIR}/node.log"
ACCOUNTS_LOG="${OUT_DIR}/accounts.txt"
ACCOUNTS_JSON="${OUT_DIR}/accounts.json"
CONFIG_JSON="${OUT_DIR}/chain_config.json"
PID_FILE="${OUT_DIR}/node.pid"
PORT_FILE="${OUT_DIR}/port.txt"

rpc_ready() {
  local resp
  resp="$(curl -s -X POST "http://${RPC_HOST}:${PORT}" \
    -H "Content-Type: application/json" \
    --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}')"
  if command -v rg >/dev/null 2>&1; then
    echo "${resp}" | rg -q '"result"'
  else
    echo "${resp}" | grep -q '"result"'
  fi
}

port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :${PORT} )" | grep -q ":${PORT} "
    return $?
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -an | grep -q ":${PORT} .*LISTEN"
    return $?
  fi
  return 1
}

port_pid() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null | head -n 1
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "( sport = :${PORT} )" 2>/dev/null | awk -F',' 'NR>1 {print $2}' | awk -F'=' '{print $2}' | head -n 1
    return 0
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -anp 2>/dev/null | awk '/:'"${PORT}"' .*LISTEN/ {print $7}' | awk -F'/' '{print $1}' | head -n 1
    return 0
  fi
  return 1
}

ensure_port_free() {
  if port_in_use; then
    echo "Port ${PORT} already in use." | tee -a "${NODE_LOG}"
    if [ -f "${PID_FILE}" ]; then
      local old_pid
      old_pid="$(cat "${PID_FILE}")"
      if kill -0 "${old_pid}" >/dev/null 2>&1; then
        echo "Stopping previous node (${old_pid})..." | tee -a "${NODE_LOG}"
        kill "${old_pid}" >/dev/null 2>&1 || true
        sleep 1
      fi
    fi
  fi
  if port_in_use; then
    local pid
    pid="$(port_pid)"
    if [ -n "${pid}" ]; then
      echo "Force killing process ${pid} on port ${PORT}." | tee -a "${NODE_LOG}"
      kill -9 "${pid}" >/dev/null 2>&1 || true
      sleep 1
    fi
  fi
  if port_in_use; then
    echo "Port ${PORT} still in use. Abort." | tee -a "${NODE_LOG}"
    exit 1
  fi
}

wait_for_rpc() {
  local tries=0
  until rpc_ready; do
    tries=$((tries + 1))
    if [ "${tries}" -gt 30 ]; then
      echo "RPC not ready after 30s" | tee -a "${NODE_LOG}"
      return 1
    fi
    sleep 1
  done
}

write_accounts() {
  python3 - <<PY
import json
import sys
import urllib.request

try:
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()
except Exception as exc:
    sys.stderr.write(f"missing eth_account: {exc}\\n")
    sys.exit(1)

cfg_path = "${CONFIG_JSON}"
with open(cfg_path, "r", encoding="utf-8") as fh:
    cfg = json.load(fh)

rpc_url = cfg.get("rpc_url")
mnemonic = cfg.get("mnemonic")
if not mnemonic:
    with open("${MNEMONIC_FILE}", "r", encoding="utf-8") as fh:
        mnemonic = fh.read().strip()
base_path = cfg.get("derivation_path", "m/44'/60'/0'/0")
count = int(cfg.get("account_count", 10))

def rpc_call(method, params):
    payload = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}).encode()
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data.get("result")

accounts = []
for idx in range(count):
    path = f"{base_path}/{idx}"
    acct = Account.from_mnemonic(mnemonic, account_path=path)
    balance_hex = rpc_call("eth_getBalance", [acct.address, "latest"])
    balance_wei = int(balance_hex, 16) if balance_hex else 0
    accounts.append({
        "index": idx,
        "address": acct.address,
        "private_key": acct.key.hex(),
        "path": path,
        "balance_wei": str(balance_wei),
    })

out_path = "${ACCOUNTS_LOG}"
with open(out_path, "w", encoding="utf-8") as fh:
    for item in accounts:
        fh.write(
            f"#{item['index']} {item['address']} {item['private_key']} "
            f"{item['path']} balance_wei={item['balance_wei']}\\n"
        )

json_path = "${ACCOUNTS_JSON}"
with open(json_path, "w", encoding="utf-8") as fh:
    json.dump({"rpc_url": rpc_url, "accounts": accounts}, fh, indent=2)
PY
}

ensure_eth_account() {
  if python3 - <<'PY' >/dev/null 2>&1; then
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("eth_account") else 1)
PY
    return 0
  fi
  if command -v pip >/dev/null 2>&1; then
    echo "Installing eth-account..." | tee -a "${NODE_LOG}"
    pip install eth-account >/dev/null 2>&1 || true
  fi
}

if ! command -v anvil >/dev/null 2>&1; then
  echo "anvil not found. Installing Foundry..." >&2
  curl -L https://foundry.paradigm.xyz | bash
  if command -v foundryup >/dev/null 2>&1; then
    foundryup
  fi
  if [ -d "${HOME}/.foundry/bin" ]; then
    export PATH="${HOME}/.foundry/bin:${PATH}"
  fi
fi
if ! command -v anvil >/dev/null 2>&1; then
  echo "anvil not found after install. Please restart your shell and try again." >&2
  exit 1
fi
ensure_port_free
NODE_CMD="anvil --host ${HOST} --port ${PORT} --mnemonic \"${MNEMONIC}\""
cat > "${CONFIG_JSON}" <<EOF
{
  "chain_type": "evm",
  "rpc_url": "http://${RPC_HOST}:${PORT}",
  "derivation_path": "m/44'/60'/0'/0",
  "account_count": 10
}
EOF
echo "Starting local chain: ${NODE_CMD}" | tee "${NODE_LOG}"
echo "${PORT}" > "${PORT_FILE}"
nohup bash -c "${NODE_CMD}" >> "${NODE_LOG}" 2>&1 &
echo $! > "${PID_FILE}"

if wait_for_rpc; then
  ensure_eth_account
  if write_accounts; then
    echo "accounts.txt generated: ${ACCOUNTS_LOG}" | tee -a "${NODE_LOG}"
    echo "accounts.json generated: ${ACCOUNTS_JSON}" | tee -a "${NODE_LOG}"
  else
    echo "failed to generate accounts.txt (missing eth_account?)" | tee -a "${NODE_LOG}"
  fi
fi

echo "Node is running. Tail logs: tail -f ${NODE_LOG}"
tail -f "${NODE_LOG}"
