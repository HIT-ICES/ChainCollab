#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORACLE_ROOT="${ORACLE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [ "$(basename "$ORACLE_ROOT")" = "04-dmn-ocr" ]; then
  ORACLE_ROOT="$(cd "$ORACLE_ROOT/.." && pwd)"
fi
CHAINLINK_ROOT="${CHAINLINK_ROOT:-$ORACLE_ROOT/CHAINLINK}"
FEATURES_04="$ORACLE_ROOT/04-dmn-ocr"
FEATURES_03="$ORACLE_ROOT/03-ocr-multinode"
export OCR_RPC_URL="${OCR_RPC_URL:-http://system-geth-node:8545}"
SYSTEM_GETH_CONTAINER="${SYSTEM_GETH_CONTAINER:-system-geth-node}"
CDMN_IMAGE="${CDMN_IMAGE:-chaincollab-cdmn-server:latest}"
CDMN_BASE_IMAGE="${CDMN_BASE_IMAGE:-python:3.9-slim}"

resolve_host_rpc_url() {
  if [ -n "${RPC_URL:-}" ]; then
    printf '%s\n' "$RPC_URL"
    return 0
  fi

  local mapped
  mapped="$(docker port "$SYSTEM_GETH_CONTAINER" 8545/tcp 2>/dev/null | head -n 1 || true)"
  if [ -n "$mapped" ]; then
    printf 'http://127.0.0.1:%s\n' "${mapped##*:}"
    return 0
  fi

  printf 'http://localhost:8545\n'
}

ensure_cdmn_image() {
  if docker image inspect "$CDMN_IMAGE" >/dev/null 2>&1; then
    echo "== [cdmn] 复用已有镜像: ${CDMN_IMAGE} =="
    return 0
  fi

  echo "== [cdmn] 首次构建镜像: ${CDMN_IMAGE} =="
  (
    cd "$FEATURES_04/cdmn-python-server"
    docker build \
      --build-arg "BASE_IMAGE=${CDMN_BASE_IMAGE}" \
      -t "$CDMN_IMAGE" \
      .
  )
}

export RPC_URL="${RPC_URL:-$(resolve_host_rpc_url)}"
echo "== [rpc] host RPC: ${RPC_URL} =="

ensure_cdmn_image

echo "== [1] 启动 OCR 多节点网络（含从节点，含 DMN 服务） =="
cd "$FEATURES_03"
./start-ocr-network.sh

echo "== [1.1] 启动 CDMN Python 服务 =="
cd "$FEATURES_04"
echo "   OCR_RPC_URL=${OCR_RPC_URL}"
docker-compose -f docker-compose-cdmn.yml up -d

echo "== [1.1] OCR 基础部署（首次或需重部署时执行） =="
cd "$CHAINLINK_ROOT"
./compile.sh
./unlock-account.sh
node scripts/deploy-chainlink.js
node "$FEATURES_03/deploy-ocr-contract.js"
node scripts/fund-chainlink-node.js --all --min 1 --amount 10
node "$FEATURES_03/fund-ocr-contract.js" --amount 100

echo "== [2] 创建 OCR Jobs（多节点） =="
cd "$CHAINLINK_ROOT"
node "$FEATURES_04/create-ocr-job-dmn.js"

echo "== [3] 配置 OCR 合约 =="
cd "$FEATURES_03"
go run gen-ocr-config.go
node set-ocr-config.js

echo "== [3.1] 同步 OCR 合约地址到 CDMN 服务并重启 =="
cd "$FEATURES_04"
if [ -f "$CHAINLINK_ROOT/deployment/ocr-deployment.json" ]; then
  OCR_AGGREGATOR_ADDRESS=$(jq -r '.contractAddress' "$CHAINLINK_ROOT/deployment/ocr-deployment.json")
  if [ -n "$OCR_AGGREGATOR_ADDRESS" ] && [ "$OCR_AGGREGATOR_ADDRESS" != "null" ]; then
    export OCR_AGGREGATOR_ADDRESS
    docker-compose -f docker-compose-cdmn.yml up -d
  else
    echo "⚠️  ocr-deployment.json 未包含 contractAddress，跳过 CDMN 服务重启"
  fi
else
  echo "⚠️  未找到 ocr-deployment.json，跳过 CDMN 服务重启"
fi

echo "== [4] 确保 DMN 请求合约已部署 =="
cd "$CHAINLINK_ROOT"
if [ ! -f deployment/deployment.json ]; then
  FORCE_DMN_CONTRACT=1 node scripts/deploy-contract.js
fi

echo "== [5] 创建 directrequest 缓存 Job（使用已部署合约地址） =="
cd "$CHAINLINK_ROOT"
EXTERNAL_JOB_ID=$(node -e "const fs=require('fs');const path=require('path');const p=path.join(process.cwd(),'deployment','chainlink-deployment.json');const data=JSON.parse(fs.readFileSync(p,'utf8'));console.log(data.dmnJobId||'');") \
  node "$FEATURES_04/create-dmn-directrequest-job.js"

echo "== [6] 将 DMN Job ID 写回合约 setJobId =="
cd "$CHAINLINK_ROOT"
node "$FEATURES_04/set-dmn-job-id.js"

echo "== [7] 设置 OCR aggregator / baseline writers =="
cd "$CHAINLINK_ROOT"
node "$FEATURES_04/set-ocr-and-writer.js"

echo "== [8] 启用 OCR finalize webhook（External Initiator） =="
# 创建 External Initiator（用于触发 webhook job）
node "$FEATURES_04/create-external-initiator.js"

# 创建 finalize webhook Job（bootstrap）
node "$FEATURES_04/create-ocr-writer-job.js"

echo "== [9] 为合约充值 LINK =="
cd "$CHAINLINK_ROOT"
node scripts/fund-contract.js

echo "== [10] 测试 directrequest 缓存链路 =="
DMN_RANDOM=1 node "$FEATURES_04/test-dmn-ocr.js"


# 手动运行 OCR ACK 监听器
# DMN_RAW_BY_HASH_URL=http://localhost:8081/api/dmn/by-hash \
# node "$FEATURES_04/ocr-ack-listener.js"

# node features/03-ocr-multinode/test-ocr-network.js
