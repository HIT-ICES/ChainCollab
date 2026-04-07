# Relayer 实验报告（正确性与开销/延迟）

生成时间：2026-04-06T11:42:31.892Z

## 1. 实验设置

- 配置文件：`/tmp/relayer-three-clean.json`
- 数据集名称：`relayer_three_clean_cases`
- BPMN 案例数：3
- 每场景实验次数：1（统一）
- 源链：chainA (31337)
- 目标链：chainB (31338)
- 执行口径：Full 与 Split 均采用“逐函数推进”执行（不是单笔占位交易）。
- 说明：部分场景在流程结构上存在重合，用于验证 Relayer 机制在相近流程模板下的稳定性。

| 场景（中文） | 场景标识 | BPMN路径 |
| --- | --- | --- |
| Coffee_machine | Coffee_machine | /home/logres/system/Experiment/CaseTest/Coffee_machine.bpmn |
| 酒店预订 | Hotel_Booking | /home/logres/system/Experiment/CaseTest/Hotel Booking.bpmn |
| 管理系统 | ManagementSystem | /home/logres/system/Experiment/CaseTest/ManagementSystem.bpmn |

## 2. 正确性与开销实验结果

| 场景 | 成功率 | Full平均Gas（gas） | Split平均Gas（gas） | 跨链附加开销（gas） | 总成本变化（gas） | 总成本变化比例 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Coffee_machine | 100.00% | 1083927.00 | 1398786.00 | 619521.00 | 314859.00 | 29.05% |
| 酒店预订 | 100.00% | 1022545.00 | 1824972.00 | 619528.00 | 802427.00 | 78.47% |
| 管理系统 | 100.00% | 944183.00 | 1540341.00 | 619562.00 | 596158.00 | 63.14% |

## 3. Latency 实验结果（按场景）

| 场景 | Full E2E均值（s, wall-clock） | Split E2E均值（s, wall-clock） | 延迟开销比例 |
| --- | ---: | ---: | ---: |
| Coffee_machine | 8.921 | 12.352 | 38.47% |
| 酒店预订 | 5.324 | 17.811 | 234.51% |
| 管理系统 | 6.031 | 14.234 | 136.00% |

## 4. 一键复现实验与导出

```bash
cd /home/logres/system/Experiment/Current/Relayer
npm install
npm run experiment:relayer:full
```

产物：
- `experiment/report/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`
- `experiment/report/relayer-unified-report.json`
- `experiment/report/LATENCY_FULL_VS_SPLIT_REPORT.md`
- `experiment/report/latency-full-vs-split-report.json`
- `experiment/report/CORRECTNESS_SPLIT_LATENCY_REPORT.md`
