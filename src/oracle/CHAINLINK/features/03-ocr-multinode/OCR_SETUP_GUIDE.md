# OCR 网络设置指南

本文档将指导您如何使用提供的脚本设置和测试 Chainlink OCR（Off-Chain Reporting）网络。

## 前置条件

1. 启动 OCR 网络（包含多个 Chainlink 节点和 Geth）：
   ```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/03-ocr-multinode
   ./start-ocr-network.sh
   ```

2. 确保您已安装所有依赖：
   ```bash
   npm install
   ```

## 流程概述

- [OCR 网络设置指南](#ocr-网络设置指南)
  - [前置条件](#前置条件)
  - [流程概述](#流程概述)
  - [1. OCR 密钥说明](#1-ocr-密钥说明)
  - [2. 编译合约](#2-编译合约)
  - [3. 部署基础合约（LinkToken/Operator）](#3-部署基础合约linktokenoperator)
  - [4. 部署 OCR 合约](#4-部署-ocr-合约)
  - [5. 收集节点信息](#5-收集节点信息)
  - [6. 为节点充值 ETH](#6-为节点充值-eth)
  - [7. 为合约充值 LINK（可选）](#7-为合约充值-link可选)
  - [8. 创建 OCR Jobs](#8-创建-ocr-jobs)
  - [9. 配置 OCR 合约](#9-配置-ocr-合约)
  - [10. 测试 OCR 网络](#10-测试-ocr-网络)
  - [验证 OCR 网络](#验证-ocr-网络)
  - [故障排除](#故障排除)
  - [文件说明](#文件说明)

---

## 1. OCR 密钥说明

Chainlink 节点启动后会自动创建 OCR 密钥、P2P 密钥和 EVM 账户，因此不需要手动生成这些密钥。

当您启动 Chainlink 节点时，它会自动：
1. 创建 EVM 账户（用于在链上发送报告）
2. 生成 P2P 密钥（用于节点间通信）
3. 生成 OCR 密钥束（用于 OCR 协议的签名和加密）

这些密钥信息将存储在节点的数据库中，并可以通过节点 UI 或 API 访问。

---

## 2. 编译合约

编译我们创建的 OCR 合约：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
./compile.sh
```

---

## 3. 部署基础合约（LinkToken/Operator）

部署 LinkToken 与 Operator 合约（供 OCR 复用）：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
./unlock-account.sh
node scripts/deploy-chainlink.js
```

部署信息将保存在 `deployment/chainlink-deployment.json` 文件中。

---

## 4. 部署 OCR 合约

部署 OCR 合约到 Geth 网络：

```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
   node features/03-ocr-multinode/deploy-ocr-contract.js
```

合约部署信息将保存在 `deployment/ocr-deployment.json` 文件中。

---

## 5. 收集节点信息

收集所有节点的详细信息（用于 OCR 网络配置）：

```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
   node features/03-ocr-multinode/get-node-info.js
```

节点信息将保存在 `deployment/node-info.json` 文件中。

---

## 6. 为节点充值 ETH

OCR 节点发送交易需要 ETH 作为 gas。批量给 `node-info.json` 里的所有节点地址充值：

```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
   node scripts/fund-chainlink-node.js --all --min 1 --amount 10
```

---

## 7. 为合约充值 LINK（可选）

`scripts/fund-contract.js` 是给 `deployment/deployment.json` 中的合约充值，
**不是 OCR 合约**。如果只做 OCR 测试，这一步可以跳过。

如需为 OCR 合约充值，请使用脚本（基于 `chainlink-deployment.json` 的 LinkToken 地址）：

```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
   node features/03-ocr-multinode/fund-ocr-contract.js --amount 100
```

---

## 8. 创建 OCR Jobs

为每个 Chainlink 节点创建 OCR Job：

```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
   node features/03-ocr-multinode/create-ocr-job.js
```

Job 信息将保存在 `deployment/chainlink-deployment.json` 文件中。

---

## 9. 配置 OCR 合约

配置 OCR 合约的 setConfig 方法，设置节点列表和参数：

```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/03-ocr-multinode
   go run gen-ocr-config.go
   node set-ocr-config.js
```

配置信息将保存在 `deployment/ocr-config.json` 文件中。

---

## 10. 测试 OCR 网络

测试 OCR 网络是否正常工作：

```bash
   cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
   node features/03-ocr-multinode/test-ocr-network.js
```

---

## 验证 OCR 网络

1. 检查每个 Chainlink 节点的日志，查看是否有 OCR 相关的信息：
   ```bash
   docker logs chainlink-node1 -f
   ```

2. 在浏览器中访问 Chainlink 节点 UI：
   - Node 1: http://localhost:6688
   - Node 2: http://localhost:6689
   - Node 3: http://localhost:6690

   使用 `admin@chain.link` 和 `change-me-strong` 登录。

3. 验证 OCR Job 是否在运行状态。

---

## 故障排除

1. **合约未编译**：确保您已运行 `./compile.sh`

2. **无法连接到节点**：检查 OCR 网络是否正常运行：
   ```bash
   ./status-ocr-network.sh
   ```

3. **价格未更新**：
   - 检查节点日志是否有错误
   - 验证所有节点的 Job 是否在运行
   - 检查节点是否有足够的 ETH 余额
   - 检查合约是否已收到 LINK 代币

---

## 文件说明

- `contracts/ocr2/` - 官方 OCR 2.0 合约集合，包括：
  - `OCR2Aggregator.sol` - 主要的 OCR 2.0 价格喂价合约
  - `OCR2Abstract.sol` - OCR 2.0 抽象合约
  - `AccessControlledOCR2Aggregator.sol` - 带有访问控制的 OCR 2.0 合约
  - `SimpleReadAccessController.sol` 和 `SimpleWriteAccessController.sol` - 简单的访问控制合约
  - 其他支持合约和接口
- `features/03-ocr-multinode/job-spec-ocr.toml` - OCR Job 的配置文件模板
- `features/03-ocr-multinode/create-ocr-keys.js` - 为所有节点创建 OCR2 密钥的脚本
- `features/03-ocr-multinode/deploy-ocr-contract.js` - 部署 OCR 合约的脚本
- `features/03-ocr-multinode/get-node-info.js` - 收集节点信息的脚本
- `features/03-ocr-multinode/create-ocr-job.js` - 为每个节点创建 OCR Job 的脚本
- `features/03-ocr-multinode/set-ocr-config.js` - 配置 OCR 合约的脚本
- `features/03-ocr-multinode/test-ocr-network.js` - 测试 OCR 网络的脚本
- `deployment/` - 保存部署信息和配置的文件夹

---

请按照上述步骤逐步执行，确保每一步都成功完成。如果遇到任何问题，请查看相关脚本的输出和 Docker 容器的日志。
