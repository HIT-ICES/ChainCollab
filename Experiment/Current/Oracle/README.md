# Oracle Experiments Workspace

## Overview

本目录已按你给的 `UnifiedOracle` 接口搭建可运行骨架，并拆分出两类实验：

1. `data`：股价采集聚合（clean / malicious）
2. `compute 10-scenarios`：10 个工业场景、每场景 2 个任务的链上直算 vs 链下计算成本对比
3. `security whitelist+signature`：白名单 + 结果签名绑定的抗攻击实验
4. `three-suite`：整体BFT / 数据聚合 / 10场景计算成本实验

## Structure

- `src/contract/UnifiedOracleLab.sol`  
  `UnifiedOracle` 的可运行实现（MEAN / MEDIAN / WEIGHTED_MEAN，签名校验，任务状态查询）。
- `src/contract/IndustrialComputeDirect.sol`  
  计算任务链上直算基线合约（数值、逻辑、混合任务）。
- `src/oracle-node/README.md`  
  预留的 Oracle 节点代码目录说明。
- `experiment/dataset/stock_price_scenarios.json`  
  data 实验数据（真实值 + clean + malicious 节点上报）。
- `experiment/dataset/industrial_data_aggregation_scenarios.json`  
  工业数据聚合实验输入（由脚本自动采集并构造）。
- `experiment/dataset/compute_payloads.json`  
  整体BFT实验的计算输入。
- `experiment/dataset/compute_tasks_10_scenarios.json`  
  10 场景计算任务数据集。
- `experiment/dataset/dmn_compute_cases.json`  
  DMN 决策任务复杂度案例集（工业互联网场景）。
- `experiment/scripts/experiment-data-stock.js`  
  data 类型实验脚本，输出聚合效果与鲁棒性。
- `experiment/scripts/prepare-industrial-data-aggregation.py`  
  自动采集 UCI 工业数据并生成聚合实验输入。
- `experiment/scripts/experiment-data-industrial-aggregation.js`  
  工业数据聚合实验脚本（无恶意节点，聚焦真实数据问题）。
- `experiment/scripts/generate-data-industrial-report.js`  
  生成工业数据聚合实验 Markdown 报告。
- `experiment/scripts/experiment-compute-10-scenarios.js`  
  10 场景计算实验脚本，输出报告表格所需字段。
- `experiment/scripts/experiment-dmn-complexity.js`  
  DMN 决策任务链上复杂度实验脚本。
- `experiment/scripts/generate-compute-unified-report.js`  
  统一生成“计算任务总报告”（Compute-10 + DMN Complexity）。
- `experiment/scripts/experiment-overall-bft.js`  
  整体拜占庭容错实验（数据+计算双侧，对比不同策略）。
- `experiment/scripts/experiment-security-whitelist-signature.js`  
  白名单 + 结果签名机制抗攻击实验（越权、伪造、篡改、重放、终态后提交）。
- `experiment/scripts/experiment-data-aggregation-benchmark.js`  
  数据聚合效果实验（恶意比例扫描、鲁棒性指标、研究对比引用）。
- `experiment/report/ORACLE_DATASET_SURVEY_AND_EXPERIMENT_PLAN.md`  
  数据集调研与实验设计文档。

## Run

```bash
cd /home/logres/system/Experiment/Current/Oracle
npm install
npm run compile
npm run experiment:data
npm run experiment:data-industrial-report
npm run experiment:three
npm run experiment:compute-10-scenarios
npm run experiment:dmn-complexity
npm run experiment:compute-unified
npm run experiment:security-whitelist-signature
```

输出结果：

- `experiment/report/data-stock-report.json`
- `experiment/report/data-industrial-aggregation-report.json`
- `experiment/report/DATA_INDUSTRIAL_AGGREGATION_REPORT.md`
- `experiment/report/experiment-overall-bft.json`
- `experiment/report/experiment-data-benchmark.json`
- `experiment/report/compute-10-scenarios-report.json`
- `experiment/report/COMPUTE_10_SCENARIOS_REPORT.md`
- `experiment/report/dmn-complexity-report.json`
- `experiment/report/DMN_COMPLEXITY_REPORT.md`
- `experiment/report/COMPUTE_UNIFIED_EXPERIMENT_REPORT.md`
- `experiment/report/security-whitelist-signature-report.json`
- `experiment/report/SECURITY_WHITELIST_SIGNATURE_REPORT.md`
