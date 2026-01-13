#!/bin/bash

# Chainlink Oracle 一键启动脚本
# 自动执行 README 中的所有启动步骤

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置信息
GETH_ACCOUNT="0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d"
GETH_PASSWORD=""
CHAINLINK_UI="http://localhost:6688"
CHAINLINK_USER="admin@chain.link"
CHAINLINK_PASS="change-me-strong"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Chainlink Oracle 一键启动脚本${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 步骤 1: 检查 Docker
echo -e "${YELLOW}[1/6] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装，请先安装 Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 环境正常${NC}"
echo ""

# 步骤 2: 停止旧服务
echo -e "${YELLOW}[2/6] 停止旧服务（如果存在）...${NC}"
docker-compose down 2>/dev/null || true
echo -e "${GREEN}✅ 旧服务已停止${NC}"
echo ""

# 步骤 3: 启动所有服务
echo -e "${YELLOW}[3/6] 启动 Docker 服务...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 服务启动失败${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 服务启动成功${NC}"
echo ""

# 步骤 4: 等待服务就绪
echo -e "${YELLOW}[4/6] 等待服务初始化...${NC}"
echo "等待 PostgreSQL 启动..."
sleep 5

echo "等待 Geth 节点启动 (IPC 准备)..."
# 先等待 IPC 文件创建
for i in {1..20}; do
    if docker exec chainlink-mybootnode-1 test -S /root/.ethereum/geth.ipc 2>/dev/null; then
        echo "IPC 文件已创建"
        break
    fi
    if [ $i -eq 20 ]; then
        echo -e "${RED}❌ Geth IPC 文件创建超时${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""

# 再等待节点完全启动
echo "等待 Geth 节点就绪..."
for i in {1..30}; do
    if docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.blockNumber" &>/dev/null; then
        echo -e "${GREEN}✅ Geth 节点已就绪${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Geth 节点启动超时${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""

echo "等待 Chainlink 节点启动..."
sleep 10

for i in {1..20}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:6688 | grep -q "200\|302"; then
        echo -e "${GREEN}✅ Chainlink 节点已就绪${NC}"
        break
    fi
    if [ $i -eq 20 ]; then
        echo -e "${RED}❌ Chainlink 节点启动超时${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""

# 步骤 5: 检查服务状态
echo -e "${YELLOW}[5/6] 检查服务状态...${NC}"
docker-compose ps

echo ""
echo "检查 Geth 账户..."
ACCOUNTS=""
for i in {1..5}; do
    ACCOUNTS=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.accounts" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$ACCOUNTS" ]; then
        break
    fi
    if [ $i -eq 5 ]; then
        echo -e "${RED}❌ 无法获取 Geth 账户列表${NC}"
        echo "尝试手动检查:"
        echo "  docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec \"eth.accounts\""
        exit 1
    fi
    echo "重试 $i/5..."
    sleep 2
done

if echo "$ACCOUNTS" | grep -q "$GETH_ACCOUNT"; then
    echo -e "${GREEN}✅ Geth 账户存在: $GETH_ACCOUNT${NC}"
else
    echo -e "${YELLOW}⚠️  警告: 账户 $GETH_ACCOUNT 不在列表中${NC}"
    echo "找到的账户: $ACCOUNTS"
    echo "这可能不影响使用,但请检查配置"
fi

echo ""
echo "检查 Chainlink 连接..."
if docker logs chainlink-node 2>&1 | tail -50 | grep -q "3456"; then
    echo -e "${GREEN}✅ Chainlink 已连接到 Chain ID 3456${NC}"
else
    echo -e "${YELLOW}⚠️  Chainlink 可能未完全连接，请稍后查看日志${NC}"
fi

echo ""

# 步骤 6: 显示访问信息
echo -e "${YELLOW}[6/6] 部署信息${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 Chainlink Oracle 启动成功！${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}📋 服务访问信息:${NC}"
echo ""
echo -e "  ${BLUE}Chainlink UI:${NC}  $CHAINLINK_UI"
echo -e "    用户名: $CHAINLINK_USER"
echo -e "    密码:   $CHAINLINK_PASS"
echo ""
echo -e "  ${BLUE}Geth RPC:${NC}      http://localhost:8545"
echo -e "  ${BLUE}PostgreSQL:${NC}    localhost:5432"
echo ""
echo -e "${YELLOW}📝 已部署合约:${NC}"
echo ""
DEPLOYMENT_DIR="deployment"
if [ -f "$DEPLOYMENT_DIR/chainlink-deployment.json" ] && command -v jq &> /dev/null; then
    LINK_ADDR=$(jq -r '.linkToken' $DEPLOYMENT_DIR/chainlink-deployment.json)
    OPERATOR_ADDR=$(jq -r '.operator' $DEPLOYMENT_DIR/chainlink-deployment.json)
    echo -e "  ${BLUE}LINK Token:${NC}  $LINK_ADDR"
    echo -e "  ${BLUE}Operator:${NC}    $OPERATOR_ADDR"
else
    echo -e "  ${BLUE}LINK Token:${NC}  (未部署)"
    echo -e "  ${BLUE}Operator:${NC}    (未部署)"
fi
echo -e "  ${BLUE}Job ID:${NC}      1e7d2a7c-fd9c-40c0-bb7f-287032908212"
echo -e "  ${BLUE}部署账户:${NC}    $GETH_ACCOUNT"
echo ""
echo -e "${YELLOW}🔧 常用命令:${NC}"
echo ""
echo -e "  查看日志:"
echo -e "    ${BLUE}docker logs chainlink-node -f${NC}"
echo -e "    ${BLUE}docker logs chainlink-mybootnode-1 -f${NC}"
echo ""
echo -e "  解锁账户:"
echo -e "    ${BLUE}./unlock-account.sh${NC}"
echo ""
echo -e "  部署合约:"
echo -e "    ${BLUE}node scripts/deploy-contract.js${NC}"
echo ""
echo -e "  停止服务:"
echo -e "    ${BLUE}docker-compose down${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}✨ 现在可以打开浏览器访问 Chainlink UI 了！${NC}"
echo ""
