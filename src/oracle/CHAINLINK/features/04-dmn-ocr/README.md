# DMN + OCR 私有工作流

本目录将 DMN 事件触发与本地 DMN 计算缓存连接起来，并将缓存作为 OCR 的观测源。
它复用本仓库已有的 DMN 服务和 OCR 配置流程。

## 组件

- DMN 请求合约（`MyChainlinkRequesterDMN.sol`）
- directrequest 缓存 Job：监听 `OracleRequest` -> 调用本地缓存 API -> 把 raw/hash 写入合约（基准）
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
- `features/04-dmn-ocr/job-spec-ocr-writer.toml`：OCR NewTransmission → finalize（webhook）
- `features/04-dmn-ocr/create-ocr-writer-job.js`：创建 OCR finalize Job（bootstrap 节点）
- `features/04-dmn-ocr/ocr-ack-listener.js`：监听 NewTransmission 并触发 finalize webhook
- `features/04-dmn-ocr/set-ocr-and-writer.js`：设置 OCR aggregator 与 baseline writers（合约配置）
- `features/04-dmn-ocr/query-raw-results.js`：查询合约 rawResults
- `features/04-dmn-ocr/compare-raw-hash.js`：对比 OCR hash 与 raw hash
- `features/04-dmn-ocr/finalize-and-query.js`：finalize 并查询 getFinalizedRaw

## 一键运行（run-setup）

以下脚本将串起 OCR 网络、CDMN 服务、合约部署、Job 创建与必要配置，适合快速联调：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
./features/04-dmn-ocr/run-setup.sh
```

如需从已有部署中继续，可先检查 `deployment/chainlink-deployment.json` 与 `deployment/deployment.json` 是否存在并包含 OCR/合约地址。

## 1) 合约请求入口

使用 `MyChainlinkRequesterDMN.sol` 的 `requestDMNDecision()` 发起请求，
节点侧的 directrequest Job 会监听 `OracleRequest` 并把参数转发到 `/api/dmn/calc`。

注意：
- `dmnContent` 过大可能超过日志限制，生产环境建议将 DMN XML 放到链下，
  仅在请求中携带 URL 或 CID。
- `inputData` 可以是 JSON 字符串，缓存服务会尝试解析。

## 2) 启动 CDMN 服务

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/04-dmn-ocr
docker-compose -f docker-compose-cdmn.yml up -d
```

说明：`start-ocr-network.sh` 会自动启动 CDMN 服务；这里用于单独启动或重启 CDMN 服务。

如需重建/重启（CDMN 服务代码有改动时）：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/04-dmn-ocr
docker-compose -f docker-compose-cdmn.yml down
docker-compose -f docker-compose-cdmn.yml build --no-cache
docker-compose -f docker-compose-cdmn.yml up -d
```

## CDMN 服务容器说明

使用 `docker-compose-cdmn.yml` 启动 CDMN 服务（默认对外端口见 compose 文件配置）。

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

## 4) 启动本地缓存服务（复用 CDMN 服务）

CDMN 服务启动后已包含缓存 API，无需额外启动新的服务。

## 5) OCR 写回监听（清缓存）

CDMN 服务已内置 OCR 事件监听（每个节点独立运行），监听到 `NewTransmission` 后自动 ACK 清缓存并打印日志。  
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

## 6.2) 同步 OCR 合约地址到 DMN 服务并重启

当 CDMN 服务启动时若 `OCR_AGGREGATOR_ADDRESS` 为空，会提示“未找到 OCR 合约地址，将以空值启动 DMN 服务”。
在 OCR 合约部署完成后，需要把地址注入环境变量并重启 CDMN 容器：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/features/04-dmn-ocr
export OCR_AGGREGATOR_ADDRESS=$(jq -r '.contractAddress' ../../deployment/ocr-deployment.json)
docker-compose -f docker-compose-cdmn.yml up -d
```

如果不想依赖环境变量，也可以在本目录 `.env` 中写入：

```
OCR_AGGREGATOR_ADDRESS=0x...
```

然后重启 DMN 容器即可生效。

## 7) 确保 DMN 请求合约已部署

如果 `deployment/deployment.json` 已存在，则直接使用其中的合约地址；
否则先部署（JobID 可先为空，后续再 `setJobId`）。

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
if [ ! -f deployment/deployment.json ]; then
  ALLOW_EMPTY_DMN_JOB_ID=1 ./deploy.sh
fi
```

## 8) 创建 directrequest 缓存 Job（使用已部署合约地址）

这是 **directrequest Job**，监听 `requestDMNDecision()` 触发的 `OracleRequest`，
调用 `/api/dmn/calc` 写缓存，并将 raw/hash 写入合约：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/create-dmn-directrequest-job.js
```

脚本会从 `deployment/chainlink-deployment.json` 读取 `operator` 作为监听合约地址，
并从 `deployment/deployment.json` 读取 DMN request 合约地址（或使用 `DMN_REQUEST_CONTRACT_ADDRESS`）。
并为每个节点创建一个 Job（自动指向 `cdmn-node1~4`）。
默认会使用第一个节点生成的 `externalJobID`，并自动用于其余节点。
创建完成后，会写入 `dmnJobIds`，并将 `dmnJobId` 设为 `chainlink1` 的 Job。

## 9) 将 DMN Job ID 写回合约 setJobId

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/set-dmn-job-id.js
```

### 设置 OCR aggregator / baseline writers

部署合约后需要设置 OCR 聚合器地址与基准写入地址（包含 bootstrap 与 chainlink1~4 的 EVM 地址）：

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/set-ocr-and-writer.js
```

### OCR finalize webhook（External Initiator）

监听 `NewTransmission` 后自动调用 `finalizeWithOcrAnswer(requestId, hashLow)`：

```bash
# 创建 External Initiator（用于触发 webhook job）
node features/04-dmn-ocr/create-external-initiator.js

# 创建 finalize webhook Job（bootstrap）
node features/04-dmn-ocr/create-ocr-writer-job.js

# 运行监听器（仅 bootstrap）
DMN_RAW_BY_HASH_URL=http://localhost:8081/api/dmn/by-hash \
node features/04-dmn-ocr/ocr-ack-listener.js
```

## 10) 为合约充值 LINK

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

使用本目录的两个 TOML 文件并替换占位符（脚本会自动替换 `DMN_CACHE_URL`、`operator` 与 `DMN_REQUEST_CONTRACT_ADDRESS`）：

1. `features/04-dmn-ocr/job-spec-dmn-event.toml`
2. `features/04-dmn-ocr/job-spec-ocr-dmn.toml`

directrequest 缓存 Job 监听 `OracleRequest` 并调用 `http://cdmn-nodeX:5000/api/dmn/calc`，
随后把 `raw/hash` 写入 DMN request 合约作为基准结果。
OCR Job 读取 `http://cdmn-nodeX:5000/api/dmn/latest?requireReady=1`，使用返回的 `hashDec` 作为 observation（数值）。
合约通过 `isOcrMatch(requestId)` 校验 OCR 的 `latestAnswer` 是否与基准 hash 一致。

注意：当前 `hashDec` 为 **raw hash 的低 128 位**，合约校验逻辑需保持一致。
另外，当没有缓存时 `/api/dmn/latest` 默认返回 **404**（ready=false），
如果带 `requireReady=1` 会返回 **409**，以避免 OCR 上报 0 覆盖最新结果。
当前 hash 使用 **keccak256(raw)**，并以其低 128 位作为 `hashDec`，需与合约一致。

## 11) 触发流程

从合约调用事件发射函数，整体流程如下：

1. 合约调用 `requestDMNDecision()`
2. directrequest 缓存 Job 触发缓存服务 `POST /dmn/calc`
3. 缓存服务调用 DMN 引擎并保存结果（返回 raw/hash/hashDec）
4. directrequest Job 调用合约 `commitBaselineFromRaw(requestId, raw)` 写入基准 raw/hash
5. OCR Job 读取 `GET /api/dmn/latest`（取 `hashDec` 作为数值观测）
6. OCR 网络聚合并写回链上
7. DMN request 合约通过 `isOcrMatch(requestId)` 校验 OCR 结果与基准 hash
8. OCR finalize webhook 自动调用 `finalize(requestId)`，结果变为可用（`getFinalizedRaw`）
8. DMN 节点内置监听器捕获 `NewTransmission` 并清缓存

说明：监听器会带上区块时间戳，服务端仅在缓存不晚于该时间戳时清除，避免误清更晚写入的数据。ACK 会记录日志并清理 cache / cache_by_hash。

## 11.1) 交互流程示意图（含原始数据写回）

```plaintext
合约调用 requestDMNDecision()
  ↓ (OracleRequest)
directrequest 缓存 Job (每节点)
  ↓ POST /api/dmn/calc
CDMN 服务 (cdmn-nodeX) 计算并缓存 rawResult
  ↓ directrequest Job: commitBaselineFromRaw(requestId, raw)
DMN request 合约存储基准 raw/hash
  ↓ GET /api/dmn/latest
OCR Job (每节点) 读取数值观测（hashDec）
  ↓ OCR 聚合/签名
OffchainAggregator 合约写回 (NewTransmission)
  ↓ 监听器解析 answer(hashLow)，通过 /by-hash 反查 requestId
  ↓ OCR finalize webhook: finalizeWithOcrAnswer(requestId, hashLow)
  ↓ DMN request 合约按 requestId 校验 isOcrMatch
  ↓ finalize(requestId) 后结果可用
  ↘  DMN 节点内置监听 (清缓存)
```

## 12) 测试 directrequest 缓存链路

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK
node features/04-dmn-ocr/test-dmn-ocr.js
```

可选环境变量：
- `DMN_URL`（默认 `http://cdmn-node1:5000/api/dmn/evaluate`）
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

如需 finalize 并读取最终结果：

```bash
# 或仅查询：
REQUEST_ID=0x9e78ccb0e3ae17558a7b7091e13abf3ec4d5642cd7723299cb893beb0f1b2efc RPC_URL=http://localhost:8545 node features/04-dmn-ocr/finalize-and-query.js --no-finalize
```
