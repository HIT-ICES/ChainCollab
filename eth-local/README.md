# 本地以太坊模拟环境（最小版）

本目录提供最小的 Hardhat 本地链环境，用于部署与测试 `AggregatingOracle` 合约。

## 快速开始
```bash
cd /home/logres/system/eth-local
npm install
npm run node
```

新开终端部署合约：
```bash
cd /home/logres/system/eth-local
npm run deploy
```

部署完成后，终端会输出合约地址。  
你可以将该地址填入 `src/oracle-node/oracle_node/config.yml` 的 `contract_address`，并用 `aggregator_node.py` 提交数据。

## 说明
- `hardhat.config.js` 固定 RPC：`http://127.0.0.1:8545`
- `scripts/deploy.js` 部署 AggregatingOracle
- `contracts/AggregatingOracle.sol` 为最小可验证合约版本
