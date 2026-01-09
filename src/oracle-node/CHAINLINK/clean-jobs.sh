#!/bin/bash

# Chainlink Jobs 清理脚本 (保留区块链数据)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Chainlink Jobs 清理脚本${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}这将删除:${NC}"
echo "  - Chainlink Jobs 和配置"
echo "  - PostgreSQL 数据库"
echo ""
echo -e "${GREEN}保留:${NC}"
echo "  - Geth 区块链数据"
echo "  - 账户 keystore"
echo "  - 已部署的合约"
echo ""

read -p "确定要继续吗? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${YELLOW}已取消操作${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/3] 停止服务...${NC}"
docker-compose stop chainlink postgres 2>/dev/null || true
echo -e "${GREEN}✅ 服务已停止${NC}"
echo ""

echo -e "${YELLOW}[2/3] 删除 PostgreSQL volume (包含 Jobs 数据)...${NC}"
docker-compose down postgres 2>/dev/null || true
docker volume rm chainlink_postgres-data 2>/dev/null || echo "Volume 不存在或已删除"
echo -e "${GREEN}✅ 数据库已清理${NC}"
echo ""

echo -e "${YELLOW}[3/3] 清理 Chainlink 运行时数据...${NC}"
if [ -d "chainlink/.chainlink" ]; then
    rm -rf chainlink/.chainlink
    echo -e "${GREEN}✅ Chainlink 运行时数据已删除${NC}"
else
    echo -e "${YELLOW}运行时数据不存在${NC}"
fi
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 清理完成！${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}下一步:${NC}"
echo ""
echo "1. 重新启动服务:"
echo -e "   ${BLUE}./start.sh${NC}"
echo ""
echo "2. 重新创建 Job:"
echo -e "   ${BLUE}node scripts/create-job.js${NC}"
echo ""
echo "3. 或者重新部署合约 (将自动创建 Job):"
echo -e "   ${BLUE}./deploy.sh${NC}"
echo ""
