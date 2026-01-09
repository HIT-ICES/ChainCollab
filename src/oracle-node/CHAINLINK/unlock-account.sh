#!/bin/bash

# Geth 账户解锁脚本

set -e

GETH_ACCOUNT="0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d"
GETH_PASSWORD=""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Geth 账户解锁脚本${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

echo -e "${YELLOW}正在解锁账户: $GETH_ACCOUNT${NC}"
echo ""

# 解锁账户 (0 表示永久解锁)
docker exec chainlink-mybootnode-1 geth --exec \
  "personal.unlockAccount('$GETH_ACCOUNT', '$GETH_PASSWORD', 0)" \
  attach /root/.ethereum/geth.ipc

echo ""
echo -e "${GREEN}✅ 账户解锁成功！${NC}"
echo ""
echo -e "${YELLOW}账户信息:${NC}"
echo -e "  地址: $GETH_ACCOUNT"
echo ""

# 查询账户余额
echo -e "${YELLOW}查询账户余额...${NC}"
BALANCE=$(docker exec chainlink-mybootnode-1 geth --exec \
  "web3.fromWei(eth.getBalance('$GETH_ACCOUNT'), 'ether')" \
  attach /root/.ethereum/geth.ipc)

echo -e "  余额: ${GREEN}$BALANCE ETH${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}现在可以部署合约了:${NC}"
echo -e "  ${BLUE}node scripts/deploy-contract.js${NC}"
echo ""
