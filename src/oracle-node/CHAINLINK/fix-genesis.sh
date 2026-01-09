#!/bin/bash

# 修复账户余额问题 - 更新 genesis.json 预分配

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEPLOY_ACCOUNT="0x7e9519a329908320829f4a747b8bac06cf0955cb"
GENESIS_FILE="geth-node/genesis.json"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  修复 Genesis 账户预分配${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

if [ ! -f "$GENESIS_FILE" ]; then
    echo -e "${RED}❌ Genesis 文件不存在: $GENESIS_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}当前 genesis.json 配置:${NC}"
cat "$GENESIS_FILE" | jq '.alloc'
echo ""

echo -e "${YELLOW}更新部署账户预分配...${NC}"
echo "账户地址: $DEPLOY_ACCOUNT"
echo "预分配金额: 10000 ETH"
echo ""

# 备份原文件
cp "$GENESIS_FILE" "${GENESIS_FILE}.backup"
echo "已备份到: ${GENESIS_FILE}.backup"

# 更新 genesis.json
cat "$GENESIS_FILE" | jq --arg addr "$DEPLOY_ACCOUNT" '.alloc[$addr] = {"balance": "10000000000000000000000"}' > "${GENESIS_FILE}.tmp"
mv "${GENESIS_FILE}.tmp" "$GENESIS_FILE"

echo -e "${GREEN}✅ Genesis 文件已更新${NC}"
echo ""

echo -e "${YELLOW}新的 genesis.json 配置:${NC}"
cat "$GENESIS_FILE" | jq '.alloc'
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}⚠️  重要: 需要重新初始化区块链${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Genesis 文件已更新，但需要重新初始化 Geth 才能生效。"
echo ""
echo -e "${YELLOW}执行以下步骤:${NC}"
echo ""
echo "1. 清理旧的区块链数据:"
echo -e "   ${BLUE}./clean.sh${NC}"
echo ""
echo "2. 重新启动服务:"
echo -e "   ${BLUE}./start.sh${NC}"
echo ""
echo "3. 部署合约:"
echo -e "   ${BLUE}./deploy.sh${NC}"
echo ""
echo "现在部署账户将自动拥有 10000 ETH!"
echo ""
