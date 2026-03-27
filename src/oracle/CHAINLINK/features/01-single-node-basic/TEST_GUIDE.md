# Chainlink Oracle 测试方案

## 概述

本测试方案用于验证 Chainlink Oracle 系统是否正常工作。我们将测试从智能合约发起链外数据请求，Chainlink 节点处理请求，外部 API 返回数据，最终智能合约接收并存储结果的完整流程。

## 测试环境要求

### 1. 服务状态检查

在开始测试前，请确保所有服务已启动：

```bash
# 检查服务状态
./status.sh
```

**预期状态**: 所有服务显示 "Up (healthy)"
- Docker 服务: 3 个服务都运行中
- Geth 节点: 运行中, 区块高度 > 0
- Chainlink 节点: 运行中, 链连接已连接 (Chain ID: 3456)
- PostgreSQL: 运行中

### 2. 部署信息

确保已完成基础部署：

```bash
ls -la deployment/
```

**预期文件**:
- `compiled.json`: 合约编译信息
- `chainlink-deployment.json`: Chainlink 基础设施信息
- `deployment.json`: 客户端合约信息

---

## 测试方案一：自动化测试（推荐）

### 步骤 1: 执行自动化测试脚本

```bash
chmod +x run-test.sh scripts/*.js
./run-test.sh
```

### 步骤 2: 自动化测试内容

脚本会自动执行以下操作：
1. 检查服务状态和部署文件
2. 为合约充值 LINK Token（如果需要）
3. 检查并充值 Chainlink 节点 ETH 账户（如果需要）
4. 启动本地测试服务器（返回 {"value": 123}）
5. 发送 Oracle 请求
6. 等待响应（30-60 秒）
7. 检查并显示结果

**预期输出**: `Value: 123`

---

## 测试方案二：手动分步骤测试

### 步骤 1: 准备部署

```bash
# 如果未部署，执行以下命令
./unlock-account.sh
node scripts/deploy-chainlink.js    # 部署 LinkToken 和 Operator
node scripts/create-job.js         # 创建 Chainlink Job
node scripts/deploy-contract.js    # 部署 MyChainlinkRequester 合约
```

### 步骤 2: 检查并充值 Chainlink 节点 ETH 账户

Chainlink 节点需要 ETH 来支付 Oracle 响应的交易费用。如果节点账户余额低于 10 ETH，需要从主账户转账：

```bash
# 检查 Chainlink 节点账户状态
node scripts/fund-chainlink-node.js
```

**功能**:
- 自动从 Chainlink 节点日志中获取节点的 ETH 账户地址
- 检查节点账户余额
- 如果余额低于 10 ETH，自动从主账户（0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d）转账 100 ETH

**预期结果**: 节点账户余额充足（> 10 ETH）

**手动转账方法（如果脚本失败）**:
```bash
# 从 Docker 容器内部转账
docker exec <mybootnode-container> geth attach /root/.ethereum/geth.ipc --exec "eth.sendTransaction({from: '0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d', to: '节点地址', value: web3.toWei(100, 'ether')})"

# 示例（使用当前 Chainlink 节点地址）
docker exec <mybootnode-container> geth attach /root/.ethereum/geth.ipc --exec "eth.sendTransaction({from: '0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d', to: '0xbB64621210982bb8504E20F1D81b2028647A5957', value: web3.toWei(100, 'ether')})"
```

### 步骤 3: 授权 Chainlink 节点地址

Chainlink 节点需要被 Operator 合约授权才能发送响应：

```bash
# 授权 Chainlink 节点地址
node scripts/authorize-chainlink-node.js
```

**功能**:
- 自动从 Chainlink 节点日志中获取节点的 ETH 账户地址
- 检查节点是否已被授权
- 如果未授权，自动调用 Operator 合约的 setAuthorizedSenders 方法进行授权

**预期结果**: 节点授权成功

**手动授权方法（如果脚本失败）**:
```bash
# 需要使用 Operator 合约的 ABI 和地址进行授权
# 通常需要通过代码或工具来完成
```

### 步骤 4: 为合约充值 LINK Token

```bash
node scripts/fund-contract.js
```

**预期结果**: 合约获得 1 LINK

### 步骤 5: 启动本地测试服务器

```bash
node scripts/test-server.js &
```

**预期输出**: 服务器运行在 http://localhost:3000，返回 {"value": 123}

### 步骤 6: 发送 Oracle 请求

```bash
node scripts/test-oracle.js
```

**预期结果**: 交易发送成功，返回交易哈希

### 步骤 7: 等待响应

等待 30-60 秒，Chainlink 节点处理请求并返回响应。

### 步骤 8: 检查结果

```bash
node scripts/check-result.js
```

**预期输出**: `Value: 123`

---

## 验证 Oracle 工作的关键指标

### 1. 查看 Chainlink 节点日志

```bash
docker logs chainlink-node -f
```

**预期日志**:
- 任务启动、解码、获取数据、解析、发送响应等过程

### 2. 访问 Chainlink UI

```
URL: http://localhost:6688
用户名: admin@chain.link
密码: change-me-strong
```

**查看内容**:
- Jobs 页面的 Job Run 记录
- 每个运行的详细信息和状态

### 3. 检查合约状态

```bash
node scripts/check-result.js
```

**预期结果**: 返回 123（非零值）

---

## 故障排除

### 1. 服务未运行

```bash
./start.sh
```

### 2. 合约未部署

```bash
./unlock-account.sh
node scripts/deploy-chainlink.js
node scripts/create-job.js
node scripts/deploy-contract.js
```

### 3. LINK 余额不足

```bash
node scripts/fund-contract.js
```

### 4. 无响应或结果为 0

检查 Chainlink 节点日志：
```bash
docker logs chainlink-node --tail 50
```

### 5. API 访问问题

确保测试服务器正在运行：
```bash
node scripts/test-server.js &
```

---

## 测试方案说明

- 使用本地测试服务器确保测试可靠性
- 测试服务器返回固定值 123，便于验证
- 整个流程覆盖了 Oracle 请求的完整生命周期
- 通过自动化脚本简化测试过程

**注意**: 测试过程中可能需要等待 1-2 分钟，Chainlink 节点需要时间处理请求。
