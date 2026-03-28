#!/bin/bash

# 停止网络的脚本

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_ROOT="$(cd "$ROOT_DIR/../.." && pwd)"
RUNTIME_CONFIG_ROOT="${CHAINCOLLAB_CHAINLINK_CONFIG_ROOT:-$SRC_ROOT/runtime/chainlink-configs/chainlink-features-03-ocr-multinode}"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose-multinode.yml"
DMN_COMPOSE_FILE="$SCRIPT_DIR/../04-dmn-ocr/docker-compose-cdmn.yml"

export CHAINLINK_BOOTSTRAP_DIR="$RUNTIME_CONFIG_ROOT/chainlink-bootstrap"
export CHAINLINK_NODE1_DIR="$RUNTIME_CONFIG_ROOT/chainlink1"
export CHAINLINK_NODE2_DIR="$RUNTIME_CONFIG_ROOT/chainlink2"
export CHAINLINK_NODE3_DIR="$RUNTIME_CONFIG_ROOT/chainlink3"
export CHAINLINK_NODE4_DIR="$RUNTIME_CONFIG_ROOT/chainlink4"

# 检查 Docker 是否正在运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误：Docker 未运行，请先启动 Docker。${NC}"
    exit 1
fi

echo -e "${BLUE}正在停止网络...${NC}"

# 停止所有节点
docker-compose -f "$COMPOSE_FILE" down
docker-compose -f "$DMN_COMPOSE_FILE" down

echo -e "${GREEN}网络已停止！${NC}"
