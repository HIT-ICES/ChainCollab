# Relayer 延迟对照实验报告（translator full vs split）

生成时间：2026-03-03T19:45:37.564Z

## 1. 实验配置

- 数据集配置：`/home/logres/system/Experiment/Current/Relayer/datasets/relayer_experiment_dataset_user3_points.json`
- 案例数：3
- 可比案例数（Full/Split 均成功）：3
- 排除案例数：0
- 业务基线时延（ms）：20000
- 源链：chainA (31337)
- 目标链：chainB (31338)

## 2. 总体对照

| 指标 | 全链上（Full） | 拆分跨链（Split） | 增量/开销 |
| --- | ---: | ---: | ---: |
| 任务数 | 30 | 30 | - |
| E2E均值(s, wall-clock) | 20.251 | 22.071 | 1.820 (8.99%) |
| 平均Gas/任务(gas) | 1184324.67 | 1798189.20 | 613864.53 (51.83%) |

## 3. 分场景对照表

| 场景 | 任务数 | Full成功率 | Full E2E均值(s) | Split成功率 | Split E2E均值(s) | 延迟开销 | Full平均Gas(gas) | Split平均Gas(gas) | 总成本变化(gas) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BikeRental | 10 | 100.00% | 20.322 | 100.00% | 22.926 | 2.603 (12.81%) | 1434903.60 | 2365191.00 | 930287.40 |
| Hotel_Booking | 10 | 100.00% | 20.282 | 100.00% | 21.638 | 1.357 (6.69%) | 986260.60 | 1516458.30 | 530197.70 |
| IncidentManagement | 10 | 100.00% | 20.150 | 100.00% | 21.649 | 1.499 (7.44%) | 1131809.80 | 1512918.30 | 381108.50 |

排除案例（不参与总体对照）：
- 无

## 4. 说明

1. Full 使用每个 BPMN 场景的 translator 生成合约（WorkflowContract）执行。
2. Split 使用 split-mode 生成的 SubmodelA/SubmodelB 合约执行，并通过 relayer 完成 handoff。
3. 两边都按“逐步骤推进”口径统计成本与端到端时延。
