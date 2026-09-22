# SupplyChainPaper 阅读入口

这份目录用于理解一条主线：

```text
BPMN 消息输入
→ B2CDSL globals 与 BusinessRule
→ Fabric / Geth 平台代码
→ 外部 DMN 请求与等待
→ finalPriority 写回
→ Gateway_0ep8cuh 四分支
```

## 建议阅读顺序

1. `FLOW_OVERVIEW.md`：先看转换期与运行期如何衔接，以及本轮能证明什么。
2. `evidence/worked_mapping_extracts.md`：看带原文件行号的关键原始片段。这是最适合论文梳理的证据文件。
3. `pim/SupplyChainPaper.b2c`：查看本轮实际生成、未经修补的完整 PIM。
4. `generated/fabric/SupplyChainPaper.go`：重点搜索 `Activity_0rm8bkp`、`Activity_0rm8bkp_Continue`、`Gateway_0ep8cuh`。
5. `generated/geth/SupplyChainPaper.sol`：搜索相同函数，比较异步请求、结果读取和状态写回。
6. `evidence/issues.md`：最后看限制、未验证事项和运行错误。

如需逐项机器检索，使用 `evidence/traceability.csv`。如需研究 Jinja renderer 的实际输入，再看 `generation_contexts/`；一般阅读不需要先看它。

## 目录中保留的原始材料

- `source_models/`：指定 BPMN 和 DMN。
- `pim/`：本次 BPMN→B2CDSL 原始输出。
- `generated/`：本次 Fabric/Go 与 Geth/Solidity 原始代码。
- `generation_contexts/`：两端实际传给 Jinja renderer 的普通 JSON context。
- `evidence/`：映射摘录、追踪表、问题和阶段状态。

完整日志、源码快照、历史候选和 typed diagnostic 均在上级完整审计归档中，不在本阅读包重复展示。
