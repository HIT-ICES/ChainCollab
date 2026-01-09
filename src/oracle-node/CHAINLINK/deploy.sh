#!/bin/bash

# 完整部署流程脚本 (含自动转账)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

GETH_ACCOUNT="0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  完整部署流程 (含自动转账)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 步骤 1: 编译合约
echo -e "${YELLOW}[1/4] 编译合约...${NC}"
if [ ! -f "compile.sh" ]; then
    echo -e "${RED}❌ compile.sh 不存在${NC}"
    exit 1
fi

./compile.sh

if [ ! -f "compiled.json" ]; then
    echo -e "${RED}❌ 编译失败，compiled.json 不存在${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 合约编译完成${NC}"
echo ""

# 步骤 2: 解锁账户并检查余额
echo -e "${YELLOW}[2/4] 解锁账户并检查余额...${NC}"

# 检查 Geth 是否运行
if ! docker ps | grep -q "chainlink-mybootnode-1"; then
    echo -e "${RED}❌ Geth 节点未运行${NC}"
    echo "请先启动服务: ./start.sh"
    exit 1
fi

./unlock-account.sh

# 检查账户余额
echo ""
echo -e "${YELLOW}检查账户余额...${NC}"
BALANCE=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.getBalance('$GETH_ACCOUNT')" 2>/dev/null)

if [ -z "$BALANCE" ] || [ "$BALANCE" = "0" ]; then
    echo -e "${YELLOW}⚠️  账户余额为 0，开始从 coinbase 转账...${NC}"

    # 获取 coinbase 地址
    COINBASE=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.coinbase" 2>/dev/null | tr -d '"')

    if [ -z "$COINBASE" ] || [ "$COINBASE" = "null" ]; then
        echo -e "${RED}❌ 无法获取 coinbase 地址${NC}"
        echo ""
        echo "可能原因:"
        echo "  - Geth 节点未完全启动"
        echo "  - 挖矿未启用"
        echo ""
        echo "尝试手动启动挖矿:"
        echo "  docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec \"miner.start()\""
        exit 1
    fi

    echo "Coinbase 地址: $COINBASE"

    # 检查 coinbase 余额
    COINBASE_BALANCE=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "web3.fromWei(eth.getBalance('$COINBASE'), 'ether')" 2>/dev/null)
    echo "Coinbase 余额: $COINBASE_BALANCE ETH"

    if [ -z "$COINBASE_BALANCE" ] || [ "$COINBASE_BALANCE" = "0" ]; then
        echo -e "${YELLOW}⚠️  Coinbase 余额不足，启动挖矿...${NC}"
        docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "miner.start()" 2>/dev/null
        echo "等待挖出一些区块 (约 10 秒)..."
        sleep 10
        docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "miner.stop()" 2>/dev/null

        # 再次检查余额
        COINBASE_BALANCE=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "web3.fromWei(eth.getBalance('$COINBASE'), 'ether')" 2>/dev/null)
        echo "Coinbase 新余额: $COINBASE_BALANCE ETH"
    fi

    # 解锁 coinbase
    echo "解锁 coinbase 账户..."
    UNLOCK_RESULT=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "personal.unlockAccount('$COINBASE', "", 0)" 2>/dev/null)

    if [ "$UNLOCK_RESULT" != "true" ]; then
        echo -e "${RED}❌ Coinbase 解锁失败${NC}"
        echo "尝试使用空密码..."
        docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "personal.unlockAccount('$COINBASE', '', 0)" 2>/dev/null
    fi

    # 从 coinbase 转账 1000 ETH
    echo "开始转账 1000 ETH 到部署账户..."
    TX_HASH=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "eth.sendTransaction({from: '$COINBASE', to: '$GETH_ACCOUNT', value: web3.toWei(1000, 'ether')})" 2>&1)

    # 检查是否有错误
    if echo "$TX_HASH" | grep -q "Error"; then
        echo -e "${RED}❌ 转账失败${NC}"
        echo "$TX_HASH"
        echo ""
        echo "请手动检查:"
        echo "  1. Coinbase 账户: docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec \"eth.coinbase\""
        echo "  2. Coinbase 余额: docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec \"web3.fromWei(eth.getBalance(eth.coinbase), 'ether')\""
        echo "  3. 手动转账: docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec \"eth.sendTransaction({from: eth.coinbase, to: '$GETH_ACCOUNT', value: web3.toWei(1000, 'ether')})\""
        exit 1
    fi

    # 清理交易哈希（去除引号）
    TX_HASH=$(echo "$TX_HASH" | tr -d '"')

    echo -e "${GREEN}✅ 转账交易已发送${NC}"
    echo "   交易哈希: $TX_HASH"
    echo "   等待交易确认 (约 5 秒)..."
    sleep 5

    # 再次检查余额
    NEW_BALANCE=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "web3.fromWei(eth.getBalance('$GETH_ACCOUNT'), 'ether')" 2>/dev/null)
    echo -e "${GREEN}✅ 转账成功! 当前余额: $NEW_BALANCE ETH${NC}"
else
    BALANCE_ETH=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "web3.fromWei(eth.getBalance('$GETH_ACCOUNT'), 'ether')" 2>/dev/null)
    echo -e "${GREEN}✅ 账户余额充足: $BALANCE_ETH ETH${NC}"
fi

echo ""

# 步骤 3: 部署合约
echo -e "${YELLOW}[3/4] 部署合约...${NC}"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js 未安装${NC}"
    exit 1
fi

# 检查并安装依赖
echo "检查项目依赖..."
if ! node -e "require.resolve('web3-eth-abi')" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  缺少依赖 web3-eth-abi，正在安装...${NC}"
    npm install web3-eth-abi
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
    echo ""
fi

# 执行部署
node scripts/deploy-contract.js

# 步骤 4: 显示结果
echo ""
echo -e "${YELLOW}[4/4] 部署结果${NC}"

if [ $? -eq 0 ] && [ -f "deployment.json" ]; then
    echo ""
    echo -e "${BLUE}================================================${NC}"
    echo -e "${GREEN}🎉 部署流程完成！${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""

    # 显示部署信息
    echo -e "${YELLOW}📝 部署信息:${NC}"
    echo ""
    if command -v jq &> /dev/null; then
        CONTRACT_ADDR=$(jq -r '.contractAddress' deployment.json)
        DEPLOYER=$(jq -r '.deployer' deployment.json)
        TIMESTAMP=$(jq -r '.timestamp' deployment.json)

        echo -e "  ${BLUE}合约地址:${NC} $CONTRACT_ADDR"
        echo -e "  ${BLUE}部署者:${NC}   $DEPLOYER"
        echo -e "  ${BLUE}时间:${NC}     $TIMESTAMP"

        # 再次获取最新余额
        FINAL_BALANCE=$(docker exec chainlink-mybootnode-1 geth attach /root/.ethereum/geth.ipc --exec "web3.fromWei(eth.getBalance('$GETH_ACCOUNT'), 'ether')" 2>/dev/null)
        echo -e "  ${BLUE}剩余余额:${NC} $FINAL_BALANCE ETH"
    else
        cat deployment.json
    fi
    echo ""

    echo -e "${YELLOW}🔧 下一步操作:${NC}"
    echo ""
    echo -e "1. 访问 Chainlink UI:"
    echo -e "   ${BLUE}http://localhost:6688${NC}"
    echo -e "   用户名: admin@chain.link"
    echo -e "   密码:   change-me-strong"
    echo ""
    echo -e "2. 查看服务状态:"
    echo -e "   ${BLUE}./status.sh${NC}"
    echo ""
    echo -e "3. 给合约转入 LINK Token (如需测试 Oracle 请求):"
    echo -e "   LINK Token: 0xb232b28da508ef56cb13b124faa0b93fcff9ff65"
    echo -e "   合约地址:   $CONTRACT_ADDR"
    echo ""
    echo -e "4. 测试 Oracle 请求:"
    echo -e "   参考 ${BLUE}README.md${NC} 中的测试步骤"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 部署失败${NC}"
    echo ""
    echo "请检查:"
    echo "  1. 查看上面的错误信息"
    echo "  2. 确认 Geth 节点正常运行: ./status.sh"
    echo "  3. 确认账户已解锁: ./unlock-account.sh"
    echo "  4. 手动部署: node scripts/deploy-contract.js"
    echo ""
    exit 1
fi
