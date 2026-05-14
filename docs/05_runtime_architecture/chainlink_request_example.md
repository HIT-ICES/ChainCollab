# 5.3 Chainlink Request Example

## 1. 当前建议采用的主线

第 5 章正文建议以 `directrequest` 为主。  
原因是：

- `features/02-single-node-dmn` 的实现链路最直接；
- 可清楚表达 “合约请求 -> DMN Service -> 回调写回”；
- OCR 扩展虽然已在仓库中有实现原型，但不宜在主线中写得过重。

## 2. directrequest Job 结构

`src/oracle-node/CHAINLINK/features/02-single-node-dmn/job-spec-dmn-java.toml` 展示了完整请求链：

1. 监听 `OracleRequest`
2. 解析请求参数
3. HTTP POST 到 DMN 服务
4. 解析结果
5. 编码回调数据
6. 调用 `fulfillOracleRequest2(...)`

## 3. 关键请求参数

合约侧传入：

- `url`
- `dmnContent`
- `decisionId`
- `inputData`

其中 `inputData` 为 JSON 字符串。

## 4. 代表性请求链

```text
requestDMNDecision(url, dmnContent, decisionId, inputData)
      ↓
OracleRequest event
      ↓
Chainlink decode_log / decode_cbor
      ↓
HTTP POST $(decode_cbor.url)
      ↓
DMN service evaluate
      ↓
fulfillOracleRequest2(...)
```

## 5. OCR 扩展说明

仓库中还存在：

- `features/04-dmn-ocr/job-spec-dmn-event.toml`
- `features/04-dmn-ocr/job-spec-ocr-dmn.toml`

这说明系统已探索了：

- directrequest baseline 写回
- OCR 聚合 hash 再校验

但若论文正文不想过度展开，建议只写一句：

> The repository also contains a prototype OCR-based extension for DMN result aggregation, but the main runtime path described in this chapter uses the simpler direct-request pattern.
