#!/bin/bash

# run-test.sh

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}  Chainlink Oracle 自动化测试${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""

# 检查服务状态
echo -e "${YELLOW}检查服务状态...${NC}"
if ! ./status.sh | grep -q "Up (healthy)"; then
    echo -e "${RED}❌ 服务未正常运行，请先启动服务: ./start.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 服务状态正常${NC}"
echo ""

# 检查部署文件
echo -e "${YELLOW}检查部署文件...${NC}"
required_files=("deployment/compiled.json" "deployment/deployment.json" "deployment/chainlink-deployment.json")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠️  文件 $file 不存在，开始部署...${NC}"
        if [ ! -f "deployment/chainlink-deployment.json" ]; then
            ./unlock-account.sh
            node scripts/deploy-chainlink.js
            node scripts/create-job.js
        fi
        node scripts/deploy-contract.js
        break
    fi
done
echo -e "${GREEN}✅ 部署文件已就绪${NC}"
echo ""

# 检查 LINK 余额
echo -e "${YELLOW}检查合约 LINK 余额...${NC}"
CONTRACT_ADDR=$(jq -r '.contractAddress' deployment/deployment.json)
LINK_ADDR=$(jq -r '.linkToken' deployment/chainlink-deployment.json)

if ! node scripts/check-link-balance.js; then
    echo -e "${YELLOW}正在为合约充值 LINK Token...${NC}"
    node scripts/fund-contract.js
fi
echo -e "${GREEN}✅ 合约 LINK 余额充足${NC}"
echo ""

# 检查并充值 Chainlink 节点 ETH 账户
echo -e "${YELLOW}检查 Chainlink 节点 ETH 账户...${NC}"
if ! node scripts/fund-chainlink-node.js; then
    echo -e "${RED}❌ Chainlink 节点账户充值失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Chainlink 节点账户准备就绪${NC}"
echo ""

# 启动测试服务器（如果需要）
echo -e "${YELLOW}启动测试服务器...${NC}"
pkill -f "node scripts/test-server.js" 2>/dev/null || true
node scripts/test-server.js &
SERVER_PID=$!

# 等待服务器启动
sleep 2

echo -e "${GREEN}✅ 测试服务器启动成功（PID: $SERVER_PID）${NC}"
echo ""

# 执行测试
echo -e "${YELLOW}执行 Oracle 请求测试...${NC}"
node scripts/test-oracle.js

echo ""
echo -e "${YELLOW}⏳ 等待 Oracle 响应（大约需要 30-60 秒）...${NC}"
echo ""
echo -e "${BLUE}可以查看 Chainlink 节点日志:${NC}"
echo "  docker logs chainlink-node -f"
echo ""
echo -e "${BLUE}或者访问 Chainlink UI:${NC}"
echo "  http://localhost:6688"
echo "  用户名: admin@chain.link"
echo "  密码: change-me-strong"
echo ""

# 等待用户输入
read -p "⏸️  按回车继续检查结果..."

# 检查结果
echo ""
echo -e "${YELLOW}检查响应结果...${NC}"
node scripts/check-result.js

# 停止测试服务器
if [ -n "$SERVER_PID" ]; then
    kill $SERVER_PID 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}🎉 测试完成！${NC}"
