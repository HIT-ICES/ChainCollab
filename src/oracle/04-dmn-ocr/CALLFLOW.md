# DMN + OCR 交互链路（04-dmn-ocr）

本目录用于把 **DMN 请求合约**、**DMN 缓存服务** 与 **OCR 网络** 串起来，形成可验证的链路。

## 参与组件

- BPMN 合约（业务侧，发起请求）
- DMN 请求合约：`MyChainlinkRequesterDMN`
- Chainlink Operator 合约
- Chainlink OCR 合约：`OffchainAggregator`
- Chainlink Jobs（directrequest / OCR / webhook）
- CDMN/DMN 服务（缓存 + DMN 计算）

## 调用链路（时序）

1. **BPMN 合约发起请求**  
   BPMN 合约调用 `MyChainlinkRequesterDMN.requestDMNDecision(...)`。

2. **DMN 请求合约触发 OracleRequest**  
   `MyChainlinkRequesterDMN` 通过 Operator 合约发出 `OracleRequest` 事件。

3. **Chainlink directrequest Job 监听并执行**  
   directrequest Job 捕获 `OracleRequest`，调用 CDMN 缓存 API（`/api/dmn/calc`），
   计算 DMN 决策并将 `raw/hash` 写回 `MyChainlinkRequesterDMN`。

4. **OCR Jobs 读取缓存作为观测值**  
   OCR Jobs 从 CDMN 缓存接口读取最新结果，作为观测值参与聚合。

5. **OCR 合约完成聚合并产生 NewTransmission**  
   OCR 合约 `OffchainAggregator` 聚合后生成 `NewTransmission` 事件。

6. **finalize webhook 回写 DMN 请求合约**  
   webhook/ack 监听捕获 `NewTransmission`，调用 `finalizeWithOcrAnswer(...)`，
   将 OCR 结果写回 `MyChainlinkRequesterDMN` 并清理缓存。

7. **BPMN 合约读取最终结果**  
   BPMN 合约从 `MyChainlinkRequesterDMN` 读取最终决策值继续流程。

## 数据流简图

```
BPMN Contract
  -> MyChainlinkRequesterDMN.requestDMNDecision()
     -> Operator OracleRequest
        -> Chainlink directrequest Job
           -> CDMN cache (DMN calc)
              -> MyChainlinkRequesterDMN(raw/hash)
                 -> OCR Jobs read cache
                    -> OffchainAggregator(NewTransmission)
                       -> finalize/webhook
                          -> MyChainlinkRequesterDMN(final result)
                             -> BPMN reads
```

## 关键文件

- `run-setup.sh`：一键启动 OCR + DMN 链路
- `job-spec-dmn-event.toml`：directrequest Job
- `job-spec-ocr-dmn.toml`：OCR Job
- `job-spec-ocr-writer.toml`：finalize webhook Job
- `create-dmn-directrequest-job.js`：创建 directrequest Job
- `create-ocr-job-dmn.js`：创建 OCR Jobs
- `create-ocr-writer-job.js`：创建 finalize webhook Job
- `set-dmn-job-id.js`：将 Job ID 写回 DMN 请求合约
- `set-ocr-and-writer.js`：配置 OCR 合约

