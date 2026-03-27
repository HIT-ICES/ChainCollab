#!/bin/bash

# Lite DMN setup:
# keep the multi-node Chainlink + DMN service stack,
# but skip all OCR-specific deployment, jobs and finalize wiring.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
FEATURES_03="$ROOT/features/03-ocr-multinode"
FEATURES_04="$ROOT/features/04-dmn-ocr"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Chainlink DMN Lite 一键启动脚本${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

echo -e "${YELLOW}[1/6] 启动多节点 Chainlink 网络与 DMN 服务...${NC}"
cd "$FEATURES_03"
./start-ocr-network.sh
echo -e "${GREEN}✅ 网络与 DMN 服务已启动${NC}"
echo ""

echo -e "${YELLOW}[2/6] 启动 CDMN 服务...${NC}"
cd "$FEATURES_04"
docker-compose -f docker-compose-cdmn.yml up -d
echo -e "${GREEN}✅ CDMN 服务已启动${NC}"
echo ""

echo -e "${YELLOW}[3/6] 编译合约并准备部署环境...${NC}"
cd "$ROOT"
./compile.sh
./unlock-account.sh
echo -e "${GREEN}✅ 合约编译与账户解锁完成${NC}"
echo ""

echo -e "${YELLOW}[4/6] 部署 Chainlink 基础设施...${NC}"
node scripts/deploy-chainlink.js
echo -e "${GREEN}✅ Chainlink 基础设施部署完成${NC}"
echo ""

echo -e "${YELLOW}[5/6] 部署 Lite 版 DMN 请求合约并创建 directrequest Job...${NC}"
DMN_MODE=lite FORCE_DMN_CONTRACT=1 node scripts/deploy-contract.js
DMN_MODE=lite node features/04-dmn-ocr/create-dmn-directrequest-job.js
DMN_MODE=lite node features/04-dmn-ocr/set-dmn-job-id.js
echo -e "${GREEN}✅ Lite DMN 合约与 Job 已就绪${NC}"
echo ""

echo -e "${YELLOW}[6/6] 为 Lite DMN 合约充值 LINK...${NC}"
node scripts/fund-contract.js
echo -e "${GREEN}✅ LINK 充值完成${NC}"
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 Chainlink DMN Lite 启动完成${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Lite 模式不包含 OCR 合约、OCR Job、OCR finalize webhook。"
echo "你现在可以直接调用 requestDMNDecision，并通过 Lite 对应接口读取结果。"
echo ""
