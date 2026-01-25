# DMN + OCR 私有工作流

本目录将 DMN 事件触发与本地 DMN 计算缓存连接起来，并将缓存作为 OCR 的观测源。
它复用本仓库已有的 DMN 服务和 OCR 配置流程。

## 组件

- DMN 事件发射合约（可添加到 `MyChainlinkRequesterDMN.sol`）
- 事件监听 Job：解码 DMNEvent -> 调用本地缓存 API
- DMN 服务新增缓存 API：执行并保存最新结果
- OCR 写回链上监听：写回后确认清缓存
- OCR Job：读取最新结果作为观测值

## 文件

- `dmn-ocr/job-spec-dmn-event.toml`：DMNEvent 监听 Job
- `dmn-ocr/job-spec-ocr-dmn.toml`：OCR Job（观测源来自本地缓存）
- `dmn-ocr/ocr-ack-listener.js`：监听 OCR 写回事件并确认清缓存

## 1) 合约事件（示例）

添加事件与触发函数（或使用独立发射合约）：

```solidity
event DMNEvent(bytes32 requestId, string dmnContent, string decisionId, string inputData);

function emitDMNEvent(
    bytes32 requestId,
    string calldata dmnContent,
    string calldata decisionId,
    string calldata inputData
) external onlyOwner {
    emit DMNEvent(requestId, dmnContent, decisionId, inputData);
}
```

注意：
- `dmnContent` 过大可能超过日志限制，生产环境建议将 DMN XML 放到链下，
  仅在事件中携带 URL 或 CID。
- `inputData` 可以是 JSON 字符串，缓存服务会尝试解析。

## 2) 启动 DMN 服务

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/scripts
./start-dmn-server-java.sh
```

## 3) 启动本地缓存服务（复用 DMN 服务）

```bash
DMN 服务启动后已包含缓存 API，无需额外启动新的服务。

## 4) 启动 OCR 写回监听（清缓存）

```bash
cd /home/shenxz-lab/code/ChainCollab/src/oracle-node/CHAINLINK/dmn-ocr
RPC_URL=http://localhost:8545 \
OCR_AGGREGATOR_ADDRESS=<YOUR_OCR_V1_AGGREGATOR_ADDRESS> \
node ocr-ack-listener.js
```

环境变量：
- `RPC_URL`（默认 `http://localhost:8545`）
- `OCR_AGGREGATOR_ADDRESS`（必填）
- `DMN_ACK_URL`（默认 `http://localhost:8080/api/dmn/ack`）

## 5) 创建 Jobs

使用本目录的两个 TOML 文件并替换占位符：

1. `dmn-ocr/job-spec-dmn-event.toml`
2. `dmn-ocr/job-spec-ocr-dmn.toml`

DMNEvent Job 监听链上事件并调用 `http://localhost:8080/api/dmn/calc`。
OCR Job 读取 `http://localhost:8080/api/dmn/latest`。

## 6) 触发流程

从合约调用事件发射函数，整体流程如下：

1. 链上触发 `DMNEvent`
2. 事件 Job 触发缓存服务 `POST /dmn/calc`
3. 缓存服务调用 DMN 引擎并保存结果
4. OCR Job 读取 `GET /api/dmn/latest`
5. OCR 网络聚合并写回链上
6. 监听器捕获 `NewTransmission` 并调用 `/api/dmn/ack` 清缓存

说明：监听器会带上区块时间戳，服务端仅在缓存不晚于该时间戳时清除，避免误清更晚写入的数据。
