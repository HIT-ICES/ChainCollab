#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORACLE_ROOT="${ORACLE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
if [ "$(basename "$ORACLE_ROOT")" = "04-dmn-ocr" ]; then
  ORACLE_ROOT="$(cd "$ORACLE_ROOT/.." && pwd)"
fi
SRC_ROOT="${SRC_ROOT:-$(cd "$ORACLE_ROOT/.." && pwd)}"
CHAINLINK_ROOT="${CHAINLINK_ROOT:-$ORACLE_ROOT/CHAINLINK}"
RUNTIME_ROOT="${RUNTIME_ROOT:-$SRC_ROOT/runtime}"
RUNTIME_DEPLOYMENT_DIR="${CHAINCOLLAB_RUNTIME_DEPLOYMENT_DIR:-$RUNTIME_ROOT/deployment}"
RUNTIME_CONFIG_ROOT="${CHAINCOLLAB_CHAINLINK_CONFIG_ROOT:-$RUNTIME_ROOT/chainlink-configs/03-ocr-multinode}"
CHAINLINK_DEPLOYMENT_BACKUP_DIR="$RUNTIME_ROOT/.chainlink-deployment-backup"
FEATURES_04="$ORACLE_ROOT/04-dmn-ocr"
FEATURES_03="$ORACLE_ROOT/03-ocr-multinode"
CHAINLINK_DEPLOYMENT_DIR="$CHAINLINK_ROOT/deployment"
OCR_COMPOSE_FILE="$FEATURES_03/docker-compose-multinode.yml"
CDMN_COMPOSE_FILE="$FEATURES_04/docker-compose-cdmn.yml"

DEPLOYMENT_FILES=(
  chainlink-deployment.json
  compiled.json
  deployment.json
  external-initiator.json
  node-info.json
  ocr-config-gen.json
  ocr-config.json
  ocr-deployment.json
  operator-abi.json
  operator-compiled.json
)

restore_chainlink_deployment_backup() {
  if [ ! -d "$CHAINLINK_DEPLOYMENT_BACKUP_DIR" ]; then
    return
  fi
  mkdir -p "$CHAINLINK_DEPLOYMENT_DIR"
  for name in "${DEPLOYMENT_FILES[@]}"; do
    rm -f "$CHAINLINK_DEPLOYMENT_DIR/$name"
    if [ -f "$CHAINLINK_DEPLOYMENT_BACKUP_DIR/$name" ]; then
      cp "$CHAINLINK_DEPLOYMENT_BACKUP_DIR/$name" "$CHAINLINK_DEPLOYMENT_DIR/$name"
    fi
  done
  rm -rf "$CHAINLINK_DEPLOYMENT_BACKUP_DIR"
}

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Oracle / DMN Lite Clean${NC}"
echo -e "${BLUE}================================================${NC}"

echo -e "${YELLOW}[1/5] 停止并清理 CDMN 容器...${NC}"
if [ -f "$CDMN_COMPOSE_FILE" ]; then
  (cd "$FEATURES_04" && docker-compose -f "$CDMN_COMPOSE_FILE" down --remove-orphans) || true
fi
echo -e "${GREEN}✅ CDMN 已停止${NC}"

echo -e "${YELLOW}[2/5] 停止并清理 OCR 多节点网络...${NC}"
if [ -f "$OCR_COMPOSE_FILE" ]; then
  (cd "$FEATURES_03" && docker-compose -f "$OCR_COMPOSE_FILE" down -v --remove-orphans) || true
fi
echo -e "${GREEN}✅ OCR 网络和数据库 volumes 已清理${NC}"

echo -e "${YELLOW}[3/5] 清理 OCR 运行时配置目录...${NC}"
rm -rf "$RUNTIME_CONFIG_ROOT"
echo -e "${GREEN}✅ OCR runtime 配置目录已清理${NC}"

echo -e "${YELLOW}[4/5] 恢复 Chainlink deployment 备份...${NC}"
restore_chainlink_deployment_backup
echo -e "${GREEN}✅ deployment 备份已恢复${NC}"

echo -e "${YELLOW}[5/5] 清理运行时 deployment 产物...${NC}"
rm -rf "$RUNTIME_DEPLOYMENT_DIR"
echo -e "${GREEN}✅ runtime deployment 已清理${NC}"

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}🎉 Oracle / DMN Lite 清理完成${NC}"
echo -e "${BLUE}================================================${NC}"
