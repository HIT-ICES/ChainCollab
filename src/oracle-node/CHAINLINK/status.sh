#!/bin/bash

# Chainlink Oracle 服务状态检查脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Chainlink Oracle 服务状态${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 检查 Docker 服务
echo -e "${YELLOW}📦 Docker 服务状态:${NC}"
docker-compose ps
echo ""

# 检查 Geth 节点
echo -e "${YELLOW}⛓️  Geth 节点状态:${NC}"
if docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.blockNumber" &>/dev/null; then
    BLOCK_NUM=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.blockNumber" 2>/dev/null)
    echo -e "  状态: ${GREEN}运行中${NC}"
    echo -e "  区块高度: ${GREEN}$BLOCK_NUM${NC}"

    MINING=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.mining" 2>/dev/null)
    if [ "$MINING" = "true" ]; then
        echo -e "  挖矿状态: ${GREEN}进行中${NC}"
    else
        echo -e "  挖矿状态: ${RED}未启动${NC}"
    fi

    PEER_COUNT=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "net.peerCount" 2>/dev/null)
    echo -e "  连接节点数: ${GREEN}$PEER_COUNT${NC}"
else
    echo -e "  状态: ${RED}未运行${NC}"
fi
echo ""

# 检查 Chainlink 节点
echo -e "${YELLOW}🔗 Chainlink 节点状态:${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6688 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo -e "  状态: ${GREEN}运行中${NC}"
    echo -e "  UI 地址: ${BLUE}http://localhost:6688${NC}"

    # 检查链连接
    if docker logs chainlink-node 2>&1 | tail -100 | grep -q "3456"; then
        echo -e "  链连接: ${GREEN}已连接 (Chain ID: 3456)${NC}"
    else
        echo -e "  链连接: ${YELLOW}检查中...${NC}"
    fi
else
    echo -e "  状态: ${RED}未运行 (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# 检查 PostgreSQL
echo -e "${YELLOW}🗄️  PostgreSQL 状态:${NC}"
if docker exec chainlink-postgres-1 pg_isready -U postgres &>/dev/null; then
    echo -e "  状态: ${GREEN}运行中${NC}"
    echo -e "  端口: ${BLUE}5432${NC}"
else
    echo -e "  状态: ${RED}未运行${NC}"
fi
echo ""

# 显示最近日志
echo -e "${YELLOW}📋 最近日志 (Chainlink):${NC}"
docker logs chainlink-node --tail 10 2>&1 | sed 's/^/  /'
echo ""

echo -e "${YELLOW}📋 最近日志 (Geth):${NC}"
docker logs chainlink-mybootnode-1 --tail 10 2>&1 | sed 's/^/  /'
echo ""

# 部署信息
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}📝 部署信息:${NC}"
echo ""
echo -e "  ${BLUE}LINK Token:${NC}  0xb232b28da508ef56cb13b124faa0b93fcff9ff65"
echo -e "  ${BLUE}Operator:${NC}    0x75cd7081c3224a11b2b013faed8606acd4cec737"
echo -e "  ${BLUE}Job ID:${NC}      85666de4-e963-484f-b342-3eaa583733ad"
echo -e "  ${BLUE}部署账户:${NC}    0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d"
echo ""

# 快捷命令
echo -e "${YELLOW}🔧 快捷命令:${NC}"
echo ""
echo -e "  查看完整日志:"
echo -e "    ${BLUE}docker logs chainlink-node -f${NC}"
echo -e "    ${BLUE}docker logs chainlink-mybootnode-1 -f${NC}"
echo ""
echo -e "  重启服务:"
echo -e "    ${BLUE}docker-compose restart${NC}"
echo ""
echo -e "  停止服务:"
echo -e "    ${BLUE}docker-compose down${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
