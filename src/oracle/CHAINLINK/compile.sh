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

SOLC_IMAGE="${SOLC_IMAGE:-ethereum/solc:0.8.19}"
SOLC_MODE="local"

if ! solc --version >/dev/null 2>&1; then
    if command -v docker &> /dev/null; then
        SOLC_MODE="docker"
        echo -e "${YELLOW}⚠️  本机 solc 不可用，切换到 Docker 编译器 ${SOLC_IMAGE}${NC}"
    else
        echo -e "${RED}❌ 本机 solc 不可用，且未安装 docker，无法继续编译${NC}"
        exit 1
    fi
fi

run_solc() {
    if [ "$SOLC_MODE" = "docker" ]; then
        docker run --rm -v "$PWD":/sources -w /sources "$SOLC_IMAGE" "$@"
    else
        solc "$@"
    fi
}

ensure_node_dependencies() {
    local chainlink_contracts_file="node_modules/@chainlink/contracts/src/v0.8/operatorforwarder/ChainlinkClient.sol"
    local missing=()

    if [ ! -f "$chainlink_contracts_file" ]; then
        missing+=("@chainlink/contracts")
    fi

    for pkg in axios dotenv web3-eth-abi; do
        if ! node -e "require.resolve('${pkg}/package.json')" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        return 0
    fi

    if ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ 缺少 npm，无法自动安装依赖${NC}"
        echo "请先安装 Node.js / npm，再重试。"
        exit 1
    fi

    echo -e "${YELLOW}⚠️  检测到 Chainlink 依赖缺失: ${missing[*]}${NC}"
    echo -e "${YELLOW}正在在 ${BLUE}$(pwd)${YELLOW} 执行 npm install（使用 npmmirror）...${NC}"
    npm install --registry=https://registry.npmmirror.com --no-fund --no-audit

    if [ ! -f "$chainlink_contracts_file" ]; then
        echo -e "${RED}❌ npm install 后仍未找到 $chainlink_contracts_file${NC}"
        exit 1
    fi
}

ensure_node_dependencies

echo -e "${YELLOW}Solidity 版本:${NC}"
run_solc --version | head -1
echo ""

# 编译合约
echo -e "${YELLOW}正在编译 MyChainlinkRequester / MyChainlinkRequesterDMN 合约...${NC}"

# 确保 deployment 文件夹存在
DEPLOYMENT_DIR="deployment"
if [ ! -d "$DEPLOYMENT_DIR" ]; then
    mkdir -p "$DEPLOYMENT_DIR"
fi

compile_contracts() {
    run_solc --optimize \
      --evm-version paris \
      --via-ir \
      --base-path . \
      --include-path node_modules \
      --include-path contracts \
      --allow-paths .,node_modules,contracts \
      @openzeppelin/=contracts/vendor/openzeppelin/ \
      @chainlink/=node_modules/@chainlink/ \
      --combined-json abi,bin \
      contracts/MyChainlinkRequester.sol \
      contracts/MyChainlinkRequesterDMN.sol \
      contracts/MyChainlinkRequesterDMN_Lite.sol \
      contracts/MainOracleRouter.sol \
      contracts/ChainlinkDataTaskAdapter.sol \
      contracts/ChainlinkComputeTaskAdapter.sol \
      contracts/CrossChainAdapter.sol \
      contracts/LinkToken-v0.6-fix/LinkToken.sol \
      contracts/LinkToken-v0.6-fix/ERC677.sol \
      contracts/LinkToken-v0.6-fix/ITypeAndVersion.sol \
      contracts/LinkToken-v0.6-fix/token/LinkERC20.sol \
      contracts/LinkToken-v0.6-fix/token/IERC677.sol \
      contracts/LinkToken-v0.6-fix/token/IERC677Receiver.sol \
      contracts/ocr/OffchainAggregator_Allequal.sol \
      contracts/ocr/AccessControlledOffchainAggregator.sol \
      contracts/ocr/OffchainAggregatorBilling.sol \
      contracts/ocr/Owned.sol \
      contracts/ocr/SimpleReadAccessController.sol \
      contracts/ocr/SimpleWriteAccessController.sol \
      contracts/ocr/AccessControllerInterface.sol \
      contracts/ocr/AggregatorInterface.sol \
      contracts/ocr/AggregatorV2V3Interface.sol \
      contracts/ocr/AggregatorV3Interface.sol \
      contracts/ocr/AggregatorValidatorInterface.sol \
      contracts/ocr/LinkTokenInterface.sol \
      contracts/ocr/TypeAndVersionInterface.sol > "$DEPLOYMENT_DIR/compiled.json"
}

if compile_contracts; then
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
    if [ "$SOLC_MODE" != "docker" ] && command -v docker &> /dev/null; then
        echo -e "${YELLOW}⚠️  本机 solc 编译失败，改用 Docker 版编译器重试${NC}"
        SOLC_MODE="docker"
        if compile_contracts; then
            echo -e "${GREEN}✅ 合约编译成功${NC}"
            echo ""
            echo -e "${YELLOW}生成的文件:${NC}"
            echo -e "  ${BLUE}deployment/compiled.json${NC} - 合约 ABI 和字节码"
            echo ""

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
            echo -e "${RED}❌ 编译失败（Docker 版编译器也失败）${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ 编译失败${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}================================================${NC}"
