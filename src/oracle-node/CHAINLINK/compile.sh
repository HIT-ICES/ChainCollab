#!/bin/bash

# 合约编译脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  合约编译脚本${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 检查 solc 是否安装
if ! command -v solc &> /dev/null; then
    echo -e "${RED}❌ solc 未安装${NC}"
    echo ""
    echo "请安装 Solidity 编译器:"
    echo "  Ubuntu/Debian: sudo apt-get install solc"
    echo "  macOS: brew install solidity"
    echo "  或使用 npm: npm install -g solc"
    exit 1
fi

echo -e "${YELLOW}Solidity 版本:${NC}"
solc --version | head -1
echo ""

# 编译合约
echo -e "${YELLOW}正在编译 MyChainlinkRequester / MyChainlinkRequesterDMN 合约...${NC}"

# 确保 deployment 文件夹存在
DEPLOYMENT_DIR="deployment"
if [ ! -d "$DEPLOYMENT_DIR" ]; then
    mkdir -p "$DEPLOYMENT_DIR"
fi

solc --optimize \
  --base-path . \
  --include-path node_modules \
  --combined-json abi,bin \
  contracts/MyChainlinkRequester.sol \
  contracts/MyChainlinkRequesterDMN.sol \
  contracts/LinkToken-v0.6-fix/LinkToken.sol \
  contracts/LinkToken-v0.6-fix/ERC677.sol \
  contracts/LinkToken-v0.6-fix/ITypeAndVersion.sol \
  contracts/LinkToken-v0.6-fix/token/LinkERC20.sol \
  contracts/LinkToken-v0.6-fix/token/IERC677.sol \
  contracts/LinkToken-v0.6-fix/token/IERC677Receiver.sol > $DEPLOYMENT_DIR/compiled.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 合约编译成功${NC}"
    echo ""
    echo -e "${YELLOW}生成的文件:${NC}"
    echo -e "  ${BLUE}deployment/compiled.json${NC} - 合约 ABI 和字节码"
    echo ""

    # 显示编译信息
    echo -e "${YELLOW}合约信息:${NC}"
    if command -v jq &> /dev/null; then
        echo "  合约数量: $(jq '.contracts | length' $DEPLOYMENT_DIR/compiled.json)"
        echo "  合约名称: $(jq -r '.contracts | keys[]' $DEPLOYMENT_DIR/compiled.json)"
    else
        echo "  (安装 jq 可查看详细信息: apt-get install jq)"
    fi
    echo ""
    echo -e "${GREEN}现在可以部署合约了:${NC}"
    echo -e "  ${BLUE}./unlock-account.sh${NC}"
    echo -e "  ${BLUE}node scripts/deploy-contract.js${NC}"
else
    echo -e "${RED}❌ 编译失败${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}================================================${NC}"
