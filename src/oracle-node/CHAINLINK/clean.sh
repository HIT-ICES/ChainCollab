#!/bin/bash

# Chainlink Oracle 完全清理脚本
# 警告: 这将删除所有数据,包括 Jobs、区块链数据、数据库等

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}================================================${NC}"
echo -e "${RED}  ⚠️  Chainlink Oracle 完全清理脚本${NC}"
echo -e "${RED}================================================${NC}"
echo ""
echo -e "${YELLOW}警告: 这将删除以下所有数据:${NC}"
echo ""
echo "  - Chainlink Jobs 和配置"
echo "  - PostgreSQL 数据库"
echo "  - Geth 区块链数据"
echo "  - Docker volumes"
echo "  - 编译产物和部署记录"
echo ""
echo -e "${RED}此操作不可恢复!${NC}"
echo ""

# 确认操作
read -p "确定要继续吗? (输入 'yes' 确认): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}已取消操作${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}开始清理...${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 步骤 1: 停止所有容器
echo -e "${YELLOW}[1/6] 停止所有容器...${NC}"
if docker-compose ps -q &>/dev/null; then
    docker-compose down
    echo -e "${GREEN}✅ 容器已停止${NC}"
else
    echo -e "${YELLOW}没有运行的容器${NC}"
fi
echo ""

# 步骤 2: 删除所有容器和网络
echo -e "${YELLOW}[2/6] 删除容器、网络和 volumes...${NC}"
docker-compose down -v 2>/dev/null || true
echo -e "${GREEN}✅ 容器和 volumes 已删除${NC}"
echo ""

# 步骤 3: 清理 Geth 数据目录 (保留 keystore)
echo -e "${YELLOW}[3/6] 清理 Geth 区块链数据...${NC}"
if [ -d "geth-node/datadir/geth" ]; then
    rm -rf geth-node/datadir/geth
    echo -e "${GREEN}✅ Geth 区块链数据已删除${NC}"
else
    echo -e "${YELLOW}Geth 数据目录不存在${NC}"
fi

# 保留 keystore,只清理其他数据
if [ -d "geth-node/datadir" ]; then
    find geth-node/datadir -mindepth 1 -maxdepth 1 ! -name 'keystore' -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✅ Geth 其他数据已清理 (keystore 保留)${NC}"
fi
echo ""

# 步骤 4: 清理 Chainlink 数据
echo -e "${YELLOW}[4/6] 清理 Chainlink 节点数据...${NC}"
# 不删除配置文件,只删除运行时数据
if [ -d "chainlink/.chainlink" ]; then
    rm -rf chainlink/.chainlink
    echo -e "${GREEN}✅ Chainlink 运行时数据已删除${NC}"
else
    echo -e "${YELLOW}Chainlink 数据目录不存在${NC}"
fi
echo ""

# 步骤 5: 清理编译和部署产物
echo -e "${YELLOW}[5/6] 清理编译和部署产物...${NC}"

CLEANED=0

# compiled.json 现在在 deployment 文件夹下，会被 rm -rf deployment 一起删除，所以不需要单独处理

DEPLOYMENT_DIR="deployment"
if [ -d "$DEPLOYMENT_DIR" ]; then
    rm -rf "$DEPLOYMENT_DIR"
    echo "  - 已删除 $DEPLOYMENT_DIR/ 文件夹"
    CLEANED=1
fi

if [ $CLEANED -eq 0 ]; then
    echo -e "${YELLOW}没有需要清理的编译产物${NC}"
else
    echo -e "${GREEN}✅ 编译产物已清理${NC}"
fi
echo ""

# 步骤 6: 清理 Docker 系统 (可选)
echo -e "${YELLOW}[6/6] 清理 Docker 系统缓存...${NC}"
read -p "是否清理 Docker 系统缓存 (悬空镜像、构建缓存等)? (y/n): " CLEAN_DOCKER

if [ "$CLEAN_DOCKER" = "y" ] || [ "$CLEAN_DOCKER" = "Y" ]; then
    echo "清理悬空镜像..."
    docker image prune -f 2>/dev/null || true

    echo "清理构建缓存..."
    docker builder prune -f 2>/dev/null || true

    echo -e "${GREEN}✅ Docker 缓存已清理${NC}"
else
    echo -e "${YELLOW}跳过 Docker 缓存清理${NC}"
fi
echo ""

# 完成
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 清理完成！${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}保留的文件:${NC}"
echo "  - geth-node/datadir/keystore/ (账户密钥)"
echo "  - chainlink/config.toml (Chainlink 配置)"
echo "  - chainlink/secrets.toml (Chainlink 密钥)"
echo "  - chainlink/.api (API 凭据)"
echo "  - chainlink/.password (钱包密码)"
echo "  - contracts/ (智能合约源码)"
echo "  - scripts/ (部署脚本)"
echo ""
echo -e "${YELLOW}已删除的数据:${NC}"
echo "  ✓ Chainlink Jobs 和运行时数据"
echo "  ✓ PostgreSQL 数据库"
echo "  ✓ Geth 区块链数据"
echo "  ✓ Docker volumes"
echo "  ✓ 编译产物 (compiled.json)"
echo "  ✓ 部署记录 (deployment.json)"
echo ""
echo -e "${GREEN}现在可以重新开始了:${NC}"
echo -e "  ${BLUE}./start.sh${NC}     # 启动服务"
echo -e "  ${BLUE}./compile.sh${NC}   # 编译合约"
echo -e "  ${BLUE}./deploy.sh${NC}    # 部署合约"
echo ""
