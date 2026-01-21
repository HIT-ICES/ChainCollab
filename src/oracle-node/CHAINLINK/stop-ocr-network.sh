#!/bin/bash

# 停止网络的脚本

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 Docker 是否正在运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误：Docker 未运行，请先启动 Docker。${NC}"
    exit 1
fi

echo -e "${BLUE}正在停止网络...${NC}"

# 停止所有节点
docker-compose -f docker-compose-multinode.yml down

echo -e "${GREEN}网络已停止！${NC}"
