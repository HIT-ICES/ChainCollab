# DMN 决策引擎服务使用指南

## 概述

本项目将原来在 Fabric 链码中的 DMN（决策模型和符号）引擎封装为一个独立的服务，并通过 Chainlink Oracle 提供区块链外部调用能力。

## DMN 服务架构

```
区块链智能合约 (MyChainlinkRequesterDMN.sol)
        ↓ 支付 LINK Token
Chainlink Operator 合约
        ↓ 触发 OracleRequest 事件
Chainlink 节点
        ↓ HTTP POST 请求（URL 由合约传入）
DMN Engine Service (Java/Spring Boot)
        ↓ 执行 DMN 决策
DMN Engine Service
        ↓ JSON 响应
Chainlink 节点
        ↓ fulfillOracleRequest2
Chainlink Operator 合约
        ↓ 回调 fulfill 函数
区块链智能合约 (保存决策结果)
```

## 服务组件

### 1. DMN 引擎服务 (Java/Spring Boot)

**位置**: `/oracle-node/CHAINLINK/features/02-single-node-dmn/dmn-server-java/`

**功能**:
- 提供 RESTful API 接口
- 支持 DMN 文件解析和决策执行
- 获取 DMN 文件的输入信息（用于前端表单生成）
- 健康检查接口
- 基于 Spring Boot 2.7.18 和 Camunda DMN Engine 7.21.0

### 2. Chainlink Job 配置

**位置**: `/oracle-node/CHAINLINK/features/02-single-node-dmn/job-spec-dmn-java.toml`

**功能**:
- 定义 DMN 决策任务执行流程（decode_log → decode_cbor → http → parse → ethtx）
- 解析合约参数（url/dmnContent/decisionId/inputData）
- 处理 DMN 服务响应并回写链上

### 3. 智能合约

**位置**: `/oracle-node/CHAINLINK/contracts/MyChainlinkRequesterDMN.sol`

**功能**:
- `requestDMNDecision()`: 发起 DMN 决策请求（合约传入 URL）
- `fulfill()`: 处理 DMN 决策响应
- `setJobId()`: 更新 Job ID（无需重部署）
- 支持配置 Job ID 和 Oracle 地址

## 快速开始

### 1. 启动 DMN 引擎服务

```bash
# 进入 DMN 功能目录
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/02-single-node-dmn

# 启动 DMN 服务
./start-dmn-server-java.sh

# 或者直接编译和运行
cd dmn-server-java
mvn clean package -DskipTests
java -jar target/dmn-server-1.0.0.jar
```

**预期输出**:
```
===============================================
DMN Decision Engine Server 已启动
版本: 1.0.0
===============================================
健康检查: GET http://localhost:8080/api/dmn/health
执行决策: POST http://localhost:8080/api/dmn/evaluate
获取决策信息: POST http://localhost:8080/api/dmn/input-info
缓存决策: POST http://localhost:8080/api/dmn/calc
读取缓存: GET http://localhost:8080/api/dmn/latest
确认清缓存: POST http://localhost:8080/api/dmn/ack
===============================================
```

### 2. 测试 DMN 服务

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/02-single-node-dmn

# 检查服务状态
./status-dmn-server-java.sh

# 使用 curl 测试健康检查
curl http://localhost:8080/api/dmn/health
```

**预期输出**:
```json
{
  "status": "ok",
  "timestamp": 1705296340123,
  "service": "DMN Decision Engine",
  "version": "1.0.0"
}
```

### 3. 创建 DMN Job

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/02-single-node-dmn

# 创建 DMN Job
node create-dmn-job.js
```

**预期输出**:
```
🎯 DMN Job 创建工具
==================================================

📄 正在读取 Job 配置文件...
🔐 正在登录 Chainlink 节点...
📍 节点地址: http://localhost:6688
✅ 登录成功
📝 正在创建 DMN Decision Engine Job...
✅ Job 创建成功!

📋 Job 信息:
   Job ID: 2e8d3b8c-ae9d-41d0-cc8f-398043019323 (external)
   名称: DMN Decision Engine (Java) Request
   类型: directrequest
   状态: pending

🚀 现在您可以使用此 Job ID 来配置合约
```

### 4. 部署 Chainlink 基础设施与合约

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK

# 编译合约
./compile.sh

# 部署 LinkToken / Operator
node scripts/deploy-chainlink.js

# 部署 DMN 请求合约
node scripts/deploy-contract.js

# 充值 Chainlink 节点账户（避免回调失败）
node scripts/fund-chainlink-node.js <nodeEthAddress>
```

### 5. 绑定 Job ID 并测试

```bash
# 设置合约的 Job ID（externalJobID）
node features/02-single-node-dmn/set-job-id-dmn.js <externalJobId>
```

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/02-single-node-dmn

# 确保 DMN 服务运行
./start-dmn-server-java.sh &

# 测试 DMN Oracle
node test-dmn-oracle.js

# 检查结果（等待 30-60 秒）
node check-dmn-result.js
```

## API 接口

### 1. 健康检查

**GET** `/api/dmn/health`

返回服务健康状态。

**响应示例**:
```json
{
  "status": "ok",
  "timestamp": 1705296340123,
  "service": "DMN Decision Engine",
  "version": "1.0.0"
}
```

### 2. 执行 DMN 决策

**POST** `/api/dmn/evaluate`

**请求体**:
```json
{
  "dmnContent": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><definitions ...>",
  "decisionId": "testDecision",
  "inputData": {
    "age": 15,
    "income": 5000
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "result": [{"Decision": "Minor"}],
  "decisionId": "testDecision",
  "timestamp": 1705296340123
}
```

### 3. 执行决策并缓存（供 OCR 读取）

**POST** `/api/dmn/calc`

**请求体**:
```json
{
  "requestId": "0x...",
  "dmnContent": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><definitions ...>",
  "decisionId": "testDecision",
  "inputData": {
    "age": 15,
    "income": 5000
  }
}
```

**响应示例**:
```json
{
  "ok": true,
  "requestId": "0x...",
  "value": [{"Decision": "Minor"}],
  "updatedAt": 1705296340123
}
```

### 4. 获取最近一次缓存结果

**GET** `/api/dmn/latest`

**响应示例**:
```json
{
  "ok": true,
  "ready": true,
  "value": [{"Decision": "Minor"}],
  "requestId": "0x...",
  "updatedAt": 1705296340123
}
```

### 5. OCR 写回确认并清缓存

**POST** `/api/dmn/ack`

**请求体**:
```json
{
  "requestId": "0x...",
  "aggregatorRoundId": 12,
  "answer": "123",
  "txHash": "0x...",
  "blockTimestampMs": 1705296340123
}
```

**响应示例**:
```json
{
  "ok": true,
  "clearedLatest": true,
  "skippedLatest": false,
  "removedByRequestId": false
}
```

### 6. 获取 DMN 输入信息

**POST** `/api/dmn/input-info`

**请求体**:
```json
{
  "dmnContent": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><definitions ...>"
}
```

**响应示例**:
```json
{
  "success": true,
  "inputs": [
    {
      "key": "input1",
      "label": "Age",
      "type": "integer",
      "name": "age"
    },
    {
      "key": "input2",
      "label": "Income",
      "type": "number",
      "name": "income"
    }
  ],
  "timestamp": 1705296340123
}
```

## Job 解析与回写说明

### Job 输入字段

Job 从合约请求中解析以下参数（CBOR）：

- `url`: DMN 服务地址（例如 `http://<host>:8080/api/dmn/evaluate`）
- `dmnContent`: DMN XML 字符串
- `decisionId`: DMN 决策 ID
- `inputData`: 输入数据 JSON 字符串

### Job 处理链路（核心节点）

- `decode_cbor`：解析合约请求参数
- `parse_input`：将 `inputData` JSON 字符串转为对象
- `fetch`：POST 到 `$(decode_cbor.url)`，body 为 JSON
- `parse`：提取结果字段（使用 gjson 路径）
- `ethabiencode`：打包回调数据并上链

当前解析路径使用：

```
result,0,result
```

对应 DMN 服务返回：

```json
{"result":[{"result":"Pasta"}], "success": true, ...}
```

## 智能合约方法

### 1. requestDMNDecision

发起 DMN 决策请求。

```solidity
function requestDMNDecision(
    string calldata url,
    string calldata dmnContent,
    string calldata decisionId,
    string calldata inputData
) external onlyOwner returns (bytes32 requestId);
```

**参数**:
- `url`: DMN 服务地址（含 `/api/dmn/evaluate`）
- `dmnContent`: DMN 文件内容（XML 字符串）
- `decisionId`: 要执行的决策 ID
- `inputData`: 输入数据（JSON 字符串）

### 2. fulfill

Chainlink 节点回调函数，保存决策结果。

```solidity
function fulfill(bytes32 _requestId, bytes memory _data)
    public recordChainlinkFulfillment(_requestId);
```

### 3. setJobId

更新合约内 Job ID（externalJobID 转 bytes32）。

```solidity
function setJobId(bytes32 _jobId) external onlyOwner;
```

### 4. getDMNResult

查看最后一次决策响应。

```solidity
function getDMNResult() external view returns (bytes memory);
```

## 故障排除

### 1. DMN 服务无法启动

**问题**: 端口 8080 被占用

**解决方案**:
```bash
# 查找占用进程
lsof -i :8080

# 终止进程
kill -9 <PID>

# 重新启动服务
./start-dmn-server-java.sh
```

### 2. Chainlink Job 创建失败

**问题**: 无法连接到 Chainlink 节点

**解决方案**:
```bash
# 检查 Chainlink 节点是否正在运行
./status.sh

# 重新启动服务
./start.sh
```

### 3. Oracle 请求无响应

**问题**: 智能合约没有收到响应

**解决方案**:
```bash
# 检查 DMN 服务日志
cat features/02-single-node-dmn/dmn-server-java/dmn-server.log

# 检查 Chainlink 节点日志
docker logs chainlink-node

# 检查合约事件
node scripts/parse-logs.js <txHash>

**常见原因**:
- Chainlink 节点账户没余额（日志提示 insufficient funds）
- Job ID 未更新或使用了旧的 internal ID
```

## 性能优化

### 1. DMN 文件优化

- 避免使用过于复杂的决策表
- 优化输入数据结构
- 考虑决策缓存机制

### 2. 服务优化

- 调整 JVM 内存配置
- 启用 HTTP 压缩
- 配置负载均衡
- 使用连接池

### 3. Chainlink 优化

- 调整 Job 执行并发度
- 优化响应时间监控
- 配置适当的超时时间

## 安全注意事项

### 1. 输入验证

- 严格验证 DMN 文件内容
- 验证输入数据格式
- 防止恶意 DMN 文件执行

### 2. 访问控制

- 限制 DMN 服务的访问 IP
- 使用 HTTPS 协议
- 配置 API 密钥认证

### 3. 合约安全

- 使用安全的 Chainlink 配置
- 定期审计智能合约
- 监控合约余额和交易

## 版本历史

### v1.0.0 (2024-01-15)

- 初始版本
- 支持基本的 DMN 决策执行
- 集成 Chainlink Oracle
- 提供完整的测试和部署流程

## 贡献

如果您发现问题或有改进建议，请创建 Issue 或提交 Pull Request。

## 许可证

本项目采用 MIT 许可证。
### 4. DMN 服务 500 或解析失败

**问题**: 请求体缺失、inputData 类型不匹配、结果解析失败

**解决方案**:
- Job 中 `http` 任务使用 `requestData`（不要用 `requestBody`）
- `inputData` 先 `jsonparse` 再传入
- 结果路径使用 `result,0,result`
