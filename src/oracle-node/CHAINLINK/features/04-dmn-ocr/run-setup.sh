#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK"
FEATURES_04="$ROOT/features/04-dmn-ocr"
FEATURES_03="$ROOT/features/03-ocr-multinode"

echo "== [1] 启动 OCR 多节点网络（含从节点，含 DMN 服务） =="
cd "$FEATURES_03"
./start-ocr-network.sh

echo "== [1.1] OCR 基础部署（首次或需重部署时执行） =="
cd "$ROOT"
./compile.sh
./unlock-account.sh
node scripts/deploy-chainlink.js
node features/03-ocr-multinode/deploy-ocr-contract.js
node scripts/fund-chainlink-node.js --all --min 1 --amount 10
node features/03-ocr-multinode/fund-ocr-contract.js --amount 100

echo "== [2] 创建 OCR Jobs（多节点） =="
cd "$ROOT"
node features/04-dmn-ocr/create-ocr-job-dmn.js

echo "== [3] 配置 OCR 合约 =="
cd "$FEATURES_03"
go run gen-ocr-config.go
node set-ocr-config.js

echo "== [4] 创建 directrequest 缓存 Job（OCR 读取用） =="
cd "$ROOT"
node features/04-dmn-ocr/create-dmn-directrequest-job.js

echo "== [5] 部署 DMN 事件合约 =="
cd "$ROOT"
./deploy.sh

echo "== [6] 设置 OCR aggregator / raw writer =="
cd "$ROOT"
node features/04-dmn-ocr/set-ocr-and-writer.js

echo "== [7] bootnode 写者监听（webhook Job + 轻量触发器） =="
# 创建 External Initiator（用于触发 webhook job）
node features/04-dmn-ocr/create-external-initiator.js

# DMN_RAW_BY_HASH_URL 指向任一 DMN 节点的 /api/dmn/by-hash
DMN_RAW_BY_HASH_URL=http://dmn-node1:8080/api/dmn/by-hash \
  node features/04-dmn-ocr/create-ocr-writer-job.js

echo "== [8] 为合约充值 LINK =="
cd "$ROOT"
node scripts/fund-contract.js

echo "== [9] 测试 directrequest 缓存链路 =="
node features/04-dmn-ocr/test-dmn-ocr.js

# node features/03-ocr-multinode/test-ocr-network.js
