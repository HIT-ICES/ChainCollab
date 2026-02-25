#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
FEATURES_04="$ROOT/features/04-dmn-ocr"
FEATURES_03="$ROOT/features/03-ocr-multinode"
CDMN_COMPOSE="${CDMN_COMPOSE:-docker-compose-cdmn.yml}"

describe_steps() {
  cat <<'EOF'
DMN+OCR 启动流程（up 时实际执行的步骤）
1) 启动 OCR 多节点网络（含从节点、含 DMN 服务）
2) 启动 CDMN Python 服务（缓存 API + OCR 监听）
3) OCR 基础部署（编译合约/解锁账户/部署/充值）
4) 创建 OCR Jobs（多节点）
5) 配置 OCR 合约（setConfig）
6) 同步 OCR 合约地址到 CDMN 服务并重启
7) 确保 DMN 请求合约已部署
8) 创建 directrequest 缓存 Job（监听 OracleRequest）
9) 将 DMN Job ID 写回合约 setJobId
10) 设置 OCR aggregator / baseline writers
11) 启用 OCR finalize webhook（External Initiator）
12) 为合约充值 LINK
13) 测试 directrequest 缓存链路
EOF
}

up() {
  "$FEATURES_04/run-setup.sh"
}

down() {
  echo "== [down] 停止 CDMN 服务 =="
  (cd "$FEATURES_04" && docker-compose -f "$CDMN_COMPOSE" down)

  echo "== [down] 停止 OCR 多节点网络 =="
  (cd "$FEATURES_03" && ./stop-ocr-network.sh)
}

status() {
  echo "== [status] CDMN 容器 =="
  (cd "$FEATURES_04" && docker-compose -f "$CDMN_COMPOSE" ps)
  echo
  echo "== [status] OCR 多节点容器 =="
  (cd "$FEATURES_03" && docker-compose -f docker-compose-multinode.yml ps)
}

help() {
  cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  up        启动 DMN+OCR 全流程
  down      关闭 CDMN + OCR 多节点网络
  status    查看 CDMN/OCR 容器状态
  steps     查看 up 中每一步做什么
  help      显示帮助

Env:
  ROOT           CHAINLINK 根目录（默认自动推断）
  CDMN_COMPOSE   CDMN compose 文件（默认 docker-compose-cdmn.yml）
EOF
}

cmd="${1:-help}"
case "$cmd" in
  up) up ;;
  down) down ;;
  status) status ;;
  steps) describe_steps ;;
  help|--help|-h) help ;;
  *) echo "Unknown command: $cmd" && help && exit 1 ;;
esac
