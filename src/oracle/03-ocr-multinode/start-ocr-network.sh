#!/bin/bash

# 启动网络的脚本，控制启动顺序：先启动 Bootstrap 节点，获取其 P2P ID，然后再启动其他节点

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose-multinode.yml"
DMN_COMPOSE_FILE="$SCRIPT_DIR/../04-dmn-ocr/docker-compose-cdmn.yml"
SYSTEM_GETH_CONTAINER="${SYSTEM_GETH_CONTAINER:-system-geth-node}"
STARTED_BOOTSTRAP=0
STARTED_CHAINLINK=0
STARTED_DMN=0

cleanup_on_failure() {
    local exit_code="$1"
    if [ "$exit_code" -eq 0 ]; then
        return
    fi

    echo -e "${YELLOW}检测到启动失败，开始回滚已启动容器...${NC}"
    set +e

    if [ "$STARTED_DMN" -eq 1 ]; then
        docker-compose -f "$DMN_COMPOSE_FILE" down >/dev/null 2>&1 || true
    fi
    if [ "$STARTED_CHAINLINK" -eq 1 ] || [ "$STARTED_BOOTSTRAP" -eq 1 ]; then
        docker-compose -f "$COMPOSE_FILE" down >/dev/null 2>&1 || true
    fi
}

trap 'exit_code=$?; trap - EXIT; cleanup_on_failure "$exit_code"; exit "$exit_code"' EXIT

ensure_system_geth_ready() {
    local container="$1"

    if ! docker ps --filter "name=^/${container}$" --format '{{.Names}}' | grep -qx "$container"; then
        echo -e "${RED}错误：未找到运行中的 system geth 容器 ${container}${NC}"
        exit 1
    fi

    if ! docker exec "$container" geth attach http://127.0.0.1:8545 --exec 'eth.blockNumber' >/dev/null 2>&1; then
        echo -e "${RED}错误：${container} 的 HTTP RPC(8545) 不可用${NC}"
        exit 1
    fi

    if ! docker exec "$container" geth attach ws://127.0.0.1:8546 --exec 'eth.blockNumber' >/dev/null 2>&1; then
        echo -e "${RED}错误：${container} 的 WS RPC(8546) 不可用${NC}"
        exit 1
    fi
}

# 检查 Docker 是否正在运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误：Docker 未运行，请先启动 Docker。${NC}"
    exit 1
fi

echo -e "${BLUE}检查外部系统链节点 ${SYSTEM_GETH_CONTAINER}...${NC}"
ensure_system_geth_ready "$SYSTEM_GETH_CONTAINER"
echo -e "${GREEN}system geth 节点已就绪，将复用其 RPC/WS。${NC}"

# 创建部署目录
mkdir -p "$ROOT_DIR/deployment"

# 步骤 1：启动 Bootstrap 节点和相关服务
echo -e "${BLUE}步骤 1：启动 Bootstrap 节点和相关服务（复用外部 system-geth-node）...${NC}"
STARTED_BOOTSTRAP=1
docker-compose -f "$COMPOSE_FILE" up -d postgres-bootstrap chainlink-bootstrap

# 等待 Bootstrap 节点启动并健康
echo -e "${YELLOW}等待 Bootstrap 节点启动和健康检查...${NC}"
BOOTSTRAP_HEALTHY=false
for i in {1..60}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:6687 | grep -q "200\|302"; then
        BOOTSTRAP_HEALTHY=true
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}错误：Bootstrap 节点启动超时。${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Bootstrap 节点未就绪，第 ${i}/60 次重试...${NC}"
    sleep 2
done

echo -e "${GREEN}Bootstrap 节点已就绪！${NC}"

# 步骤 2：获取 Bootstrap 节点的 P2P ID
echo -e "${BLUE}步骤 2：获取 Bootstrap 节点的 P2P ID...${NC}"
BOOTSTRAP_PEER_ID=""
for i in {1..30}; do
    # 使用 get-node-info.js 脚本获取 Bootstrap 节点的 P2P ID
    node "$SCRIPT_DIR/get-node-info.js" bootstrap > /dev/null 2>&1
    if [ -f "$ROOT_DIR/deployment/node-info.json" ]; then
        BOOTSTRAP_PEER_ID=$(jq -r '.[] | select(.name == "bootstrap") | .p2pPeerId' "$ROOT_DIR/deployment/node-info.json")
        if [ -n "$BOOTSTRAP_PEER_ID" ] && [ "$BOOTSTRAP_PEER_ID" != "null" ]; then
            break
        fi
    fi
    echo -e "${YELLOW}无法获取 Bootstrap 节点的 P2P ID，第 ${i}/30 次重试...${NC}"
    sleep 2
done

if [ -z "$BOOTSTRAP_PEER_ID" ] || [ "$BOOTSTRAP_PEER_ID" = "null" ]; then
    echo -e "${RED}错误：无法获取 Bootstrap 节点的 P2P ID。${NC}"
    exit 1
fi
echo -e "${GREEN}Bootstrap 节点 P2P ID：${BOOTSTRAP_PEER_ID}${NC}"

# 步骤 3：更新其他节点的配置，使用 Bootstrap 节点的 P2P ID
echo -e "${BLUE}步骤 3：更新其他节点的配置，使用 Bootstrap 节点的 P2P ID...${NC}"
BOOTSTRAP_IP="172.31.61.180"
BOOTSTRAP_MULTIADDR="${BOOTSTRAP_PEER_ID}@${BOOTSTRAP_IP}:6690"
# 更新其他四个节点的配置
for node in chainlink1 chainlink2 chainlink3 chainlink4; do
    # 强制更新 DefaultBootstrappers 为实际的 Bootstrap 地址（兼容单行/多行/缺失）
    python3 - "$SCRIPT_DIR/$node/config.toml" "$BOOTSTRAP_MULTIADDR" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
boot = sys.argv[2]
text = path.read_text()
new_line = f'DefaultBootstrappers = ["{boot}"]'

# Normalize any literal "\n" sequences left by earlier runs.
text = text.replace("\\n", "\n")

# Remove existing DefaultBootstrappers (single-line or multi-line block), then insert one clean line.
text = re.sub(r'^DefaultBootstrappers\s*=\s*\[.*?\n\]', '', text, flags=re.S | re.M)
text = re.sub(r'^DefaultBootstrappers\s*=\s*\[.*\]$', '', text, flags=re.M)

if re.search(r'^AnnounceAddresses = \[.*\]$', text, flags=re.M):
    text = re.sub(r'^(AnnounceAddresses = \[.*\])$', r'\1\n' + new_line, text, flags=re.M)
else:
    text = text.rstrip() + '\n' + new_line + '\n'

text = re.sub(r'\n{3,}', '\n\n', text)
path.write_text(text)
PY
done

# 步骤 3.5：获取所有节点的 OCR Key Bundle ID
echo -e "${BLUE}步骤 3.5：获取所有节点的 OCR Key Bundle ID...${NC}"
node "$SCRIPT_DIR/get-node-info.js"

# 步骤 4：启动其他四个 Chainlink 节点
echo -e "${BLUE}步骤 4：启动其他四个 Chainlink 节点...${NC}"
STARTED_CHAINLINK=1
docker-compose -f "$COMPOSE_FILE" up -d chainlink1 chainlink2 chainlink3 chainlink4

# 步骤 4.5：更新 AnnounceAddresses 为宿主机 IP 并重启节点
echo -e "${BLUE}步骤 4.5：更新 AnnounceAddresses 为宿主机 IP...${NC}"
for node in chainlink1 chainlink2 chainlink3 chainlink4; do
    if [ "$node" = "chainlink1" ]; then
        PORT=6698
    elif [ "$node" = "chainlink2" ]; then
        PORT=6699
    elif [ "$node" = "chainlink3" ]; then
        PORT=6697
    else
        PORT=6696
    fi
    sed -i "s|AnnounceAddresses = \\[\".*\"\\]|AnnounceAddresses = [\"${BOOTSTRAP_IP}:${PORT}\"]|g" "$SCRIPT_DIR/$node/config.toml"
done
docker-compose -f "$COMPOSE_FILE" restart chainlink1 chainlink2 chainlink3 chainlink4

# 等待其他节点启动并健康
echo -e "${YELLOW}等待其他节点启动和健康检查...${NC}"
ALL_NODES_HEALTHY=true
for node in chainlink-node1 chainlink-node2 chainlink-node3 chainlink-node4; do
    NODE_HEALTHY=false
    PORT=6688
    if [ "$node" = "chainlink-node2" ]; then
        PORT=6689
    elif [ "$node" = "chainlink-node3" ]; then
        PORT=6691
    elif [ "$node" = "chainlink-node4" ]; then
        PORT=6692
    fi
    for i in {1..60}; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT | grep -q "200\|302"; then
            NODE_HEALTHY=true
            break
        fi
        if [ $i -eq 60 ]; then
            echo -e "${RED}错误：${node} 启动超时。${NC}"
            ALL_NODES_HEALTHY=false
            break
        fi
        echo -e "${YELLOW}${node} 未就绪，第 ${i}/60 次重试...${NC}"
        sleep 2
    done
    if [ "$NODE_HEALTHY" = true ]; then
        echo -e "${GREEN}${node} 已就绪！${NC}"
    fi
done

if [ "$ALL_NODES_HEALTHY" = false ]; then
    echo -e "${RED}部分节点启动失败，请检查日志。${NC}"
    exit 1
fi

# 步骤 5：收集所有节点信息
echo -e "${BLUE}步骤 5：收集所有节点信息...${NC}"
node "$SCRIPT_DIR/get-node-info.js"

echo -e "${BLUE}步骤 6：启动 CDMN 服务...${NC}"
STARTED_DMN=1
OCR_DEPLOYMENT="$ROOT_DIR/deployment/ocr-deployment.json"
if [ -f "$OCR_DEPLOYMENT" ] && command -v jq &> /dev/null; then
    OCR_AGGREGATOR_ADDRESS=$(jq -r '.contractAddress' "$OCR_DEPLOYMENT")
fi
if [ -z "$OCR_AGGREGATOR_ADDRESS" ] || [ "$OCR_AGGREGATOR_ADDRESS" = "null" ]; then
    echo -e "${YELLOW}⚠️  未找到 OCR 合约地址，将以空值启动 DMN 服务${NC}"
fi
OCR_AGGREGATOR_ADDRESS="$OCR_AGGREGATOR_ADDRESS" docker-compose -f "$DMN_COMPOSE_FILE" up -d

echo -e "${GREEN}网络启动完成！${NC}"
echo -e "可以通过以下 URL 访问节点："
echo -e "  Bootstrap 节点：http://localhost:6687"
echo -e "  Node 1：http://localhost:6688"
echo -e "  Node 2：http://localhost:6689"
echo -e "  Node 3：http://localhost:6691"
echo -e "  Node 4：http://localhost:6692"
echo -e "用户名：admin@chain.link"
echo -e "密码：change-me-strong"
