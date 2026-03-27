# Relayer 实验问题总结

本文件用于记录本轮 Relayer 实验在配置调整、目录重整与重跑过程中遇到的问题，以及对应处理方式，便于论文写作时解释实验口径变化。

## 1. 已归档的旧结果

在重新启用固定出块时间模式前，已将原有报告留档到：

- `experiment/report/archive-20260323-025858`

其中包含旧版 `RELAYER_UNIFIED_EXPERIMENT_REPORT.md`、`relayer-unified-report.json` 以及相关中间结果文件。

## 2. 本轮实验的最终口径

本轮可复现的最终实验参数为：

- `RELAYER_TIMING_PROFILE=realistic`
- `ANVIL_BLOCK_TIME=3`
- `RELAYER_LATENCY_BASELINE_MS=0`
- `RELAYER_RUNS_PER_CASE=1`
- `RELAYER_DELIVERY_TIMEOUT_MS=600000`

对应的当前结果文件为：

- `experiment/report/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`
- `experiment/report/relayer-unified-report.json`
- `experiment/report/LATENCY_FULL_VS_SPLIT_REPORT.md`
- `experiment/report/latency-full-vs-split-report.json`
- `experiment/report/CORRECTNESS_SPLIT_LATENCY_REPORT.md`
- `experiment/report/correctness-split-latency-report.json`

## 3. 主要问题与处理

### 3.1 artifact 路径与新目录结构不一致

问题：
- 代码库重整后，Hardhat 产物实际输出到 `artifacts/src/contract/...`。
- 旧脚本仍在读取 `artifacts/contracts/generated/...`，导致 split worker 和正确性脚本报错。

处理：
- 增加了 `contractArtifactPath()`，统一兼容新旧两套布局。
- 更新了 `experiment-correctness-split-latency.js`、`split-worker.js` 与 `worker.js` 的 artifact 读取逻辑。

### 3.2 `acceptHandoff` 重载调用歧义

问题：
- 生成合约里存在两个同名重载函数 `acceptHandoff(...)`。
- ethers 在运行时无法自动分派，报出 `ambiguous function description`。

处理：
- 改为显式调用完整签名：
  - `acceptHandoff(bytes32,bytes32,uint256,address,uint256,bytes[])`

### 3.3 固定出块时间下，默认 delivery timeout 不足

问题：
- 启用 `ANVIL_BLOCK_TIME=3` 后，原默认 `RELAYER_DELIVERY_TIMEOUT_MS=180000` 不够。
- 在较长流程场景下会出现 `wait delivery timeout`。

处理：
- 将实验重跑时的 delivery timeout 提升到 `600000 ms`。

### 3.4 3 秒出块 + 10 次重复过慢

问题：
- 3 秒固定出块下，如果每个场景仍跑 10 次，整体耗时过长，不适合作为当前轮完整结果。

处理：
- 最终用于导出报告的口径改为 `RELAYER_RUNS_PER_CASE=1`。
- 这样可以保证 10 个场景完整跑通，同时保留固定出块时间带来的真实延迟特征。

## 4. 当前报告中仍需核对的点

### 4.1 `Exactly-once` 指标口径

现象：
- 当前 `CORRECTNESS_SPLIT_LATENCY_REPORT.md` 中 `Exactly-once 通过率` 仍显示为 `0.00%`。

判断：
- 这更像是统计口径或脚本计算逻辑的问题，而不是链上执行失败。
- 当前实验中 `submitted = 10`、`delivered = 10`、`payloadMatched = 10`、`successRate = 100%`、`payloadIntegrityRate = 100%`，说明请求处理本身是成功的。

建议：
- 论文正文中优先使用“成功率、载荷一致率、端到端时延、Gas 开销”。
- `Exactly-once` 指标建议在后续再单独核对脚本定义，或暂时不要作为主结论指标。

## 5. 结论性说明

本轮 Relayer 实验最终采用了“固定出块时间 + 无人工时延基线”的更真实口径。
相比此前的 20 秒人工基线方式，这次结果更能反映跨链执行自身带来的时延与 Gas 代价。

