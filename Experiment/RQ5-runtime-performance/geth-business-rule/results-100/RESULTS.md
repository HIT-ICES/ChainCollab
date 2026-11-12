# Geth BusinessRule 真实 Chainlink 链路测量

状态：passed；有效轮次：100。

| 阶段 | 均值(ms) | 中位数(ms) | 最小(ms) | 最大(ms) |
|---|---:|---:|---:|---:|
| API Invoker (BRT request) | 55.78 | 52.70 | 44.48 | 213.05 |
| BPMN SC / DMN request | 13154.67 | 9741.48 | 1769.04 | 44957.92 |
| DMN request to Chainlink job | 34136.37 | 34129.85 | 6133.00 | 59512.87 |
| Executor / off-chain DMN evaluation | 28.74 | 25.15 | 14.86 | 216.12 |
| IPFS / DMN download | 6.72 | 5.58 | 3.75 | 53.23 |
| DMN result commit / event receipt | 10895.66 | 9839.16 | 1159.61 | 24026.91 |
| API Invoker2 (BPMN Continue) | 66.37 | 59.14 | 46.37 | 224.57 |
| BPMN SC / apply DMN result | 12734.61 | 9106.86 | 1468.53 | 69283.77 |

阈值（ms，严格大于才排除）：{"Result commit on chain": 25000, "Request to Chainlink job": 60000}。
累计尝试：145；排除：45。排除样本不计入下表；归档清理后仅保留分类计数。

逐轮阶段明细见 [timings.csv](timings.csv)，各轮完整原始证据见 `round-*/result.json`。

端到端（首次请求至 Continue 成功事件）均值：58293.76 ms。

阶段名称明确区分 DMN 请求、链下规则执行、规则文件下载、结果回写和 BPMN 应用结果。Executor 包含 DMN 下载与计算，尚未单独计量纯规则计算耗时。

Request to Chainlink job从首次业务请求开始，包含前面的API/链上等待，与其重叠；不是Fabric的Event Bus指标。
Chainlink Executor从实际获胜节点的Job创建至其CDMN HTTP调用返回。Result commit on chain包含其后提交结果、交易确认与FireFly事件记录。
IPFS为该实际CDMN节点内部GET请求的只读网络观测，完整响应字节与原DMN哈希一致；不是脚本额外发起的替代下载。
最终BPMN Continue SC只读取已回链结果并更新流程；DMN实际计算在链下CDMN，不能与Fabric链内DMN SC直接等同。
