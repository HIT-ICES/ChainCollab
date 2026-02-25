#!/usr/bin/env bash

# Geth 账户解锁脚本（基于 RPC）

set -euo pipefail

GETH_ACCOUNT="${GETH_ACCOUNT:-0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d}"
GETH_PASSWORD="${GETH_PASSWORD:-}"
RPC_URL="${RPC_URL:-http://localhost:8545}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

rpc_call() {
  local method="$1"
  local params="$2"
  curl -sS -H 'Content-Type: application/json' \
    --data "{\"jsonrpc\":\"2.0\",\"method\":\"${method}\",\"params\":${params},\"id\":1}" \
    "${RPC_URL}"
}

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Geth 账户解锁脚本${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}RPC_URL: ${RPC_URL}${NC}"

echo -e "${YELLOW}正在解锁账户: $GETH_ACCOUNT${NC}"
echo ""

ACCOUNTS_JSON="$(rpc_call "eth_accounts" '[]' || true)"
if [[ -z "${ACCOUNTS_JSON}" ]]; then
  echo -e "${RED}❌ 无法连接 RPC: ${RPC_URL}${NC}"
  exit 1
fi

if [[ "${ACCOUNTS_JSON,,}" != *"${GETH_ACCOUNT,,}"* ]]; then
  echo -e "${RED}❌ 账户不在 eth_accounts 中: ${GETH_ACCOUNT}${NC}"
  echo "返回: ${ACCOUNTS_JSON}"
  exit 1
fi

UNLOCK_JSON="$(rpc_call "personal_unlockAccount" "[\"${GETH_ACCOUNT}\",\"${GETH_PASSWORD}\",0]" || true)"
UNLOCK_OK=0
if [[ "${UNLOCK_JSON}" == *'"result":true'* ]]; then
  UNLOCK_OK=1
elif [[ "${UNLOCK_JSON}" == *"does not exist"* ]] || [[ "${UNLOCK_JSON}" == *"is not available"* ]]; then
  echo -e "${YELLOW}⚠️  personal API 不可用，跳过显式 unlock（依赖节点启动参数 --unlock）${NC}"
  UNLOCK_OK=1
else
  echo -e "${RED}❌ unlock 失败${NC}"
  echo "返回: ${UNLOCK_JSON}"
fi

if [[ "${UNLOCK_OK}" -ne 1 ]]; then
  exit 1
fi

echo ""
echo -e "${GREEN}✅ 账户解锁成功！${NC}"
echo ""
echo -e "${YELLOW}账户信息:${NC}"
echo -e "  地址: $GETH_ACCOUNT"
echo ""

# 查询账户余额
echo -e "${YELLOW}查询账户余额...${NC}"
BAL_HEX="$(rpc_call "eth_getBalance" "[\"${GETH_ACCOUNT}\",\"latest\"]" | sed -n 's/.*"result":"\([^"]*\)".*/\1/p')"
BALANCE="$(node -e "const h='${BAL_HEX:-0x0}'; const v=BigInt(h||'0x0'); const e=v/10n**18n; const f=(v%10n**18n).toString().padStart(18,'0').replace(/0+$/,'').slice(0,6); process.stdout.write(f? \`\${e}.\${f}\`:\`\${e}\`);")"

echo -e "  余额: ${GREEN}$BALANCE ETH${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}现在可以部署合约了:${NC}"
echo -e "  ${BLUE}node scripts/deploy-contract.js${NC}"
echo ""
