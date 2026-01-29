# DMN + OCR 私有工作流

本目录将 DMN 事件触发与本地 DMN 计算缓存连接起来，并将缓存作为 OCR 的观测源。
它复用本仓库已有的 DMN 服务和 OCR 配置流程。

## 组件

- DMN 请求合约（`MyChainlinkRequesterDMN.sol`）
- directrequest 缓存 Job：监听 `OracleRequest` -> 调用本地缓存 API
- DMN 服务新增缓存 API：执行并保存最新结果
- OCR 写回链上监听：写回后确认清缓存
- OCR Job：读取最新结果作为观测值

## 文件

- `features/04-dmn-ocr/job-spec-dmn-event.toml`：DMN directrequest 缓存 Job（监听 OracleRequest）
- `features/04-dmn-ocr/job-spec-ocr-dmn.toml`：OCR Job（观测源来自本地缓存）
- `features/04-dmn-ocr/docker-compose-dmn.yml`：DMN 多节点服务编排
- `features/04-dmn-ocr/create-dmn-directrequest-job.js`：创建 DMN directrequest 缓存 Job
- `features/04-dmn-ocr/delete-dmn-event-job.js`：删除 DMN 事件监听 Job
- `features/04-dmn-ocr/create-ocr-job-dmn.js`：创建 OCR Jobs（观测源为 DMN）
- `features/04-dmn-ocr/test-dmn-ocr.js`：测试 directrequest 缓存链路
- `features/04-dmn-ocr/job-spec-ocr-writer.toml`：OCR NewTransmission → 写 raw 到合约 Job（webhook）
- `features/04-dmn-ocr/create-ocr-writer-job.js`：创建 OCR Writer Job（bootstrap 节点）
- `features/04-dmn-ocr/ocr-ack-listener.js`：bootstrap 触发 webhook Job（NewTransmission）
- `features/04-dmn-ocr/set-ocr-and-writer.js`：设置 OCR aggregator 与 raw writer（合约配置）
- `features/04-dmn-ocr/query-raw-results.js`：查询合约 rawResults
- `features/04-dmn-ocr/compare-raw-hash.js`：对比 OCR hash 与 raw hash

## 1) 合约请求入口

使用 `MyChainlinkRequesterDMN.sol` 的 `requestDMNDecision()` 发起请求，
节点侧的 directrequest Job 会监听 `OracleRequest` 并把参数转发到 `/api/dmn/calc`。

注意：
- `dmnContent` 过大可能超过日志限制，生产环境建议将 DMN XML 放到链下，
  仅在请求中携带 URL 或 CID。
- `inputData` 可以是 JSON 字符串，缓存服务会尝试解析。

## 2) 启动 DMN 服务（每个节点一个实例）

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/04-dmn-ocr
docker-compose -f docker-compose-dmn.yml up -d
```

说明：`start-ocr-network.sh` 会自动启动 DMN 服务；这里用于单独启动或重启 DMN 服务。
宿主机可访问端口：`8081~8084`（对应 dmn-node1~4）。

如需重建/重启（DMN 服务代码有改动时）：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/04-dmn-ocr
docker-compose -f docker-compose-dmn.yml down
docker-compose -f docker-compose-dmn.yml build --no-cache
docker-compose -f docker-compose-dmn.yml up -d
```

## DMN 服务容器说明

为每个 Chainlink 节点启动一个 DMN 服务容器（`dmn-node1` ~ `dmn-node4`），
默认对外映射端口：

- dmn-node1: `http://localhost:8081`
- dmn-node2: `http://localhost:8082`
- dmn-node3: `http://localhost:8083`
- dmn-node4: `http://localhost:8084`

容器内部端口均为 `8080`，Chainlink 节点在 Docker 网络内通过 `http://dmn-nodeX:8080` 访问。

## 3) 启动 OCR 多节点网络（含从节点）

参考 `features/03-ocr-multinode/OCR_SETUP_GUIDE.md`：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/03-ocr-multinode
./start-ocr-network.sh
```

如果尚未完成 OCR 基础部署，可按以下命令快速完成（摘自 OCR_SETUP_GUIDE）：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
./compile.sh
./unlock-account.sh
node scripts/deploy-chainlink.js
node features/03-ocr-multinode/deploy-ocr-contract.js
node features/03-ocr-multinode/get-node-info.js
node scripts/fund-chainlink-node.js --all --min 1 --amount 10
node features/03-ocr-multinode/fund-ocr-contract.js --amount 100
```

## 4) 启动本地缓存服务（复用 DMN 服务）

DMN 服务启动后已包含缓存 API，无需额外启动新的服务。

## 5) OCR 写回监听（清缓存）

DMN 服务已内置 OCR 事件监听（每个节点独立运行），无需单独启动脚本。  
`start-ocr-network.sh` 会从 `deployment/ocr-deployment.json` 读取 `contractAddress` 并注入 `OCR_AGGREGATOR_ADDRESS`。

### 部署建议（两类监听）

**各节点缓存监听（只清缓存）**：  
DMN 服务已内置 OCR 事件监听（通过 `ocr.listener.enabled`），无需单独运行脚本。  
`start-ocr-network.sh` 会从 `deployment/ocr-deployment.json` 读取 `contractAddress` 并注入 `OCR_AGGREGATOR_ADDRESS`。

## 6) 创建 OCR Jobs（多节点）

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/create-ocr-job-dmn.js
```

## 6.1) 配置 OCR 合约

配置 OCR 合约的 `setConfig`，设置节点列表和参数：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/03-ocr-multinode
go run gen-ocr-config.go
node set-ocr-config.js
```

配置信息会保存到 `deployment/ocr-config.json`。

## 7) 创建 directrequest 缓存 Job（OCR 读取用）

这是 **directrequest Job**，监听 `requestDMNDecision()` 触发的 `OracleRequest`，
仅调用 `/api/dmn/calc` 写缓存，供 OCR 读取：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/create-dmn-directrequest-job.js
# 可选：指定统一 externalJobID
# EXTERNAL_JOB_ID=<uuid> node features/04-dmn-ocr/create-dmn-directrequest-job.js
```

脚本会从 `deployment/chainlink-deployment.json` 读取 `operator` 作为监听合约地址，
并为每个节点创建一个 Job（自动指向 `dmn-node1~4`）。
默认会使用第一个节点生成的 `externalJobID`，并自动用于其余节点。
创建完成后，会写入 `dmnJobIds`，并将 `dmnJobId` 设为 `chainlink1` 的 Job（供部署合约使用）。

## 8) 部署 DMN 事件合约

使用上一步的 Job ID 部署 `MyChainlinkRequesterDMN.sol`（构造函数需要 Job ID）：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
./deploy.sh
```

部署完成后，记录该合约地址（用于 `requestDMNDecision()` 调用方配置）。

### 设置 OCR aggregator / raw writer

部署合约后需要设置 OCR 聚合器地址与写入者地址（bootstrap 节点 EVM 地址）：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/set-ocr-and-writer.js
```

### bootnode 写者监听（webhook Job + 轻量触发器）

在 bootstrap 节点创建 Job（NewTransmission → 读取 raw → 写合约）并启动触发器：

```bash
# 创建 External Initiator（用于触发 webhook job）
node features/04-dmn-ocr/create-external-initiator.js

# DMN_RAW_BY_HASH_URL 指向任一 DMN 节点的 /api/dmn/by-hash
DMN_RAW_BY_HASH_URL=http://dmn-node1:8080/api/dmn/by-hash \
node features/04-dmn-ocr/create-ocr-writer-job.js

# 运行轻量触发器（仅 bootstrap）
DMN_RAW_BY_HASH_URL=http://dmn-node1:8080/api/dmn/by-hash \
node features/04-dmn-ocr/ocr-ack-listener.js
```

监听器直接使用 `deployment/ocr-deployment.json` 中的 `contractAddress`。

## 8.1) 为合约充值 LINK

`requestDMNDecision()` 会消耗 LINK 作为费用，若合约余额不足会直接 revert。

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node scripts/fund-contract.js
```

如需删除：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/delete-dmn-event-job.js <jobInternalId|externalJobId>
```

使用本目录的两个 TOML 文件并替换占位符（脚本会自动替换 `DMN_CACHE_URL` 与 `operator`）：

1. `features/04-dmn-ocr/job-spec-dmn-event.toml`
2. `features/04-dmn-ocr/job-spec-ocr-dmn.toml`

directrequest 缓存 Job 监听 `OracleRequest` 并调用 `http://dmn-nodeX:8080/api/dmn/calc`。
OCR Job 读取 `http://dmn-nodeX:8080/api/dmn/latest`，使用返回的 `hashDec` 作为 observation（数值）。
bootnode 触发器会拼好 `fetchURL = http://dmn-nodeX:8080/api/dmn/by-hash?hash=<ocrAnswer>` 并放进 webhook body，
writer Job 直接使用 `fetchURL` 拉取 raw。

注意：当前 `hashDec` 为 **raw hash 的低 128 位**，合约校验逻辑需保持一致。

## 9) 触发流程

从合约调用事件发射函数，整体流程如下：

1. 合约调用 `requestDMNDecision()`
2. directrequest 缓存 Job 触发缓存服务 `POST /dmn/calc`
3. 缓存服务调用 DMN 引擎并保存结果
4. OCR Job 读取 `GET /api/dmn/latest`（取 `hashDec` 作为数值观测）
5. OCR 网络聚合并写回链上
6. DMN 节点内置监听器捕获 `NewTransmission` 并清缓存
7. bootnode 触发器监听 `NewTransmission` → 拼好 `fetchURL` → webhook Job 拉取 `/api/dmn/by-hash` → `ethtx` 写回合约

说明：监听器会带上区块时间戳，服务端仅在缓存不晚于该时间戳时清除，避免误清更晚写入的数据。

## 9.1) 交互流程示意图（含原始数据写回）

```plaintext
合约调用 requestDMNDecision()
  ↓ (OracleRequest)
directrequest 缓存 Job (每节点)
  ↓ POST /api/dmn/calc
DMN 服务 (dmn-nodeX) 计算并缓存 rawResult
  ↓ GET /api/dmn/latest
OCR Job (每节点) 读取数值观测（hashDec）
  ↓ OCR 聚合/签名
OffchainAggregator 合约写回 (NewTransmission)
  ↓ 事件监听器 (ocr-ack-listener.js)
  ↘  DMN 节点内置监听 (清缓存)
  ↘  bootnode Job: GET /api/dmn/by-hash → ethtx 写 rawResults
```

## 10) 测试 directrequest 缓存链路

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/test-dmn-ocr.js
```

可选环境变量：
- `DMN_URL`（默认 `http://dmn-node1:8080/api/dmn/evaluate`）
- `DMN_CACHE_HOSTS`（默认 `http://localhost:8081,http://localhost:8082,http://localhost:8083,http://localhost:8084`）
- `DMN_INPUT_DATA`（直接传入 JSON 字符串）
- `DMN_TEMPERATURE`（整数温度，配合 `DMN_DAY_TYPE`）
- `DMN_DAY_TYPE`（`Weekday` / `Weekend`）
- `DMN_RANDOM=1`（自动生成不同温度与 dayType）

示例：
```bash
# 直接指定输入
DMN_INPUT_DATA='{"temperature":5,"dayType":"Weekend"}' node features/04-dmn-ocr/test-dmn-ocr.js

# 随机输入（每次不同）
DMN_RANDOM=1 node features/04-dmn-ocr/test-dmn-ocr.js

# 仅改温度/类型
DMN_TEMPERATURE=25 DMN_DAY_TYPE=Weekday node features/04-dmn-ocr/test-dmn-ocr.js
```

可在最后用脚本验证合约是否写入 rawResults：

```bash
RPC_URL=http://localhost:8545 node features/04-dmn-ocr/query-raw-results.js
```
