# Relayer 实验方案（已补充 2：全链上 vs 拆分跨链延迟对照）

## 1. 目标

- `1` 正确性规模实验：验证 BPMN 拆分后的跨链子模型在中继链路上可正确到达、不篡改、不重复。
- `2` 延迟对照实验：同场景下比较全链上（Full）与拆分跨链（Split）的端到端延迟。
- `3` 故障恢复实验：验证 relayer 崩溃/重启后的最终一致与恢复时间。

## 2. 案例来源与拆分流程

案例来源（`/home/logres/system/Experiment/CaseTest`，偏工业互联网）：

- `SupplyChain.bpmn`
- `Manufactory.bpmn`
- `Coffee_machine.bpmn`

自动化拆分与生成流程：

1. 使用 `analyze_bpmn_sese.py` 提取 SESE 子模型。
2. 使用 `generator.bpmn_to_dsl` 生成 `.b2c`。
3. 使用 `textx --target solidity` 生成 Solidity 合约草案。
4. 生成拆分 DSL（主合约拆分点、子合约起止点、handoff 事件）。
5. 自动生成两份子合约（SubmodelA / SubmodelB），并用于跨链部署实验。

拆分 DSL 语法草案：`dsl/bpmn_split.ebnf`

> 说明：拆分能力已并入 `newTranslator` 主代码，通过 `--split-mode` 开关启用。未启用时会忽略 BPMN `splitPoint` 标记并保持原有行为。

输出文件：

- `datasets/bpmn_split_cases.json`
- `deployments/bpmn-split-cases.json`
- `runtime/translator/split_dsl/*.split.dsl`
- `contracts/generated/*SubmodelA.sol`
- `contracts/generated/*SubmodelB.sol`

## 3. 实验脚本

- `scripts/prepare-bpmn-split-cases.js`
- `scripts/deploy-split-generated.js`
- `scripts/experiment-correctness-split-latency.js`
- `scripts/experiment-latency-full-vs-split.js`
- `scripts/experiment-fault-recovery.js`
- `scripts/export-unified-report.js`
- 一键执行：`scripts/run-experiment-split-main.sh`
- 全量一键 + 报告导出：`scripts/run-experiment-relayer-full.sh`

数据集配置文件：

- `datasets/relayer_experiment_dataset.json`

## 4. 复现指令

```bash
cd /home/logres/system/Experiment/Relayer
npm install
npm run experiment:split:main
```

全量导出（推荐用于论文）：

```bash
npm run experiment:relayer:full
```

关闭链环境：

```bash
npm run chain:down
```

## 5. 结果文件

- `deployments/CORRECTNESS_SCALED_REPORT.md`
- `deployments/CORRECTNESS_SPLIT_LATENCY_REPORT.md`
- `deployments/correctness-split-latency-report.json`
- `deployments/FAULT_RECOVERY_REPORT.md`
- `deployments/fault-recovery-report.json`
- `deployments/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`
- `deployments/relayer-unified-report.json`

## 6. 指标

正确性与 latency 实验：

- success rate
- payload integrity rate
- exactly-once rate
- chain end-to-end latency (avg/p95)
