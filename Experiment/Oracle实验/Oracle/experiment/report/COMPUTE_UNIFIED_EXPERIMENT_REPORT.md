# 计算任务统一实验报告（Compute + DMN）

生成时间：2026-03-03T14:40:06.931Z

## 1. 实验设计

### 1.1 目标
- 评估不同计算任务在链上执行的成本差异。
- 评估“链下计算 + 链上确认”相对“直接链上计算”的成本收益。
- 针对 DMN 决策逻辑，量化模型复杂度与链上 gas 的关系。

### 1.2 实验组成
1. `Compute-10`：10 个工业场景、20 个任务（数值/逻辑/混合）直接链上 vs 链下确认。
2. `DMN-Complexity`：10 个 DMN 案例（DecisionTable/Scorecard/DecisionGraph）链上复杂度基准。

### 1.3 成本口径
- `directGas`：任务在业务合约中直接执行交易的 `gasUsed`。
- `offchainGas`：`registerComputeTask + submitComputeResultBatch` 的链上总 `gasUsed`。
- `optimizationRatio`：`(directGas - offchainGas) / directGas`。

## 2. 数据集介绍

| 数据集 | Compute 场景数 | Compute 任务数 | DMN 场景数 | DMN 案例数 | 链接 |
| --- | ---: | ---: | ---: | ---: | --- |
| UCI Steel Industry Energy Consumption | 2 | 4 | 0 | 0 | - |
| UCI SECOM | 2 | 4 | 4 | 4 | https://archive.ics.uci.edu/dataset/179/secom |
| SWaT | 2 | 4 | 1 | 1 | https://itrust.sutd.edu.sg/itrust-labs_datasets/dataset_info/ |
| WADI | 2 | 4 | 1 | 1 | https://itrust.sutd.edu.sg/itrust-labs_datasets/dataset_info/ |
| BATADAL | 1 | 2 | 2 | 2 | https://www.batadal.net/data.html |
| NASA C-MAPSS | 1 | 2 | 2 | 2 | https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data |

## 3. 实验结果展示

### 3.1 Compute-10 总体结果

| 指标 | 数值 |
| --- | ---: |
| 场景数 | 10 |
| 任务数 | 20 |
| 平均 direct gas | 4,599,024.15 |
| 平均 offchain gas | 443,289 |
| 全量链下相对优化 | 90.36% |
| 自适应调度相对全 direct 优化 | 95.32% |
| 路由分布（direct/offchain） | 11/9 |

| 路径胜率 | 占比 |
| --- | ---: |
| offchain 更优 | 45.00% |
| direct 更优 | 55.00% |

### 3.2 Compute-10 代表性任务

#### Offchain 最优 Top5

| 任务 | directGas | offchainGas | 节省Gas | 优化比例 |
| --- | ---: | ---: | ---: | ---: |
| 预测性维修优化 | 13,619,132 | 441,607 | 13,177,525 | 96.76% |
| 配水调度优化 | 12,486,621 | 441,561 | 12,045,060 | 96.46% |
| 供水路径优化 | 11,731,632 | 441,573 | 11,290,059 | 96.24% |
| 管网重构优化 | 10,976,632 | 441,568 | 10,535,064 | 95.98% |
| 多单元联动优化 | 10,238,720 | 441,573 | 9,797,147 | 95.69% |

#### Offchain 不适用 Top5（direct 更优）

| 任务 | directGas | offchainGas | 额外Gas | 优化比例 |
| --- | ---: | ---: | ---: | ---: |
| 班次能耗结算 | 46,166 | 475,826 | 429,660 | -930.68% |
| 工位放行判定 | 24,105 | 441,607 | 417,502 | -1732.01% |
| 风险驱动调度判定 | 24,781 | 441,602 | 416,821 | -1682.02% |
| 质检门限判定 | 28,923 | 441,590 | 412,667 | -1426.78% |
| 设备运行风险评分 | 29,028 | 441,554 | 412,526 | -1421.13% |

### 3.3 DMN 复杂度结果

| 指标 | 数值 |
| --- | ---: |
| 案例数 | 10 |
| 平均链上 gas | 1,044,030.1 |
| 最小链上 gas | 46,770 |
| 最大链上 gas | 5,323,135 |
| 非 DecisionGraph 最大 gas | 163,861 |
| DecisionGraph 最小 gas | 487,777 |

| DMN 模型 | 平均Gas | 最小Gas | 最大Gas |
| --- | ---: | ---: | ---: |
| DecisionTable-FIRST | 103,650.5 | 77,791 | 129,510 |
| DecisionTable-COLLECT | 121,755 | 79,649 | 163,861 |
| Scorecard | 69,170 | 46,770 | 91,570 |
| DecisionGraph | 2,462,787.5 | 487,777 | 5,323,135 |

## 4. 实验结果分析

1. 任务分层现象明显：
- 轻量任务（结算/门控/风险）direct gas 常在 29,925 左右；
- 重负载优化任务 direct gas 常在 10,183,478 量级。

2. 链下计算价值主要来自复杂任务：
- offchain 仅在 9/20 任务中获胜，但这些任务贡献了绝大多数节省。
- 采用自适应路由后，总体优化高于统一策略。

3. DMN 复杂逻辑链上开销随结构复杂度快速增长：
- DecisionTable / Scorecard 在低维规则下可链上直算；
- DecisionGraph 进入高复杂区后，链上成本显著跃升。

4. 统一结论（针对计算任务）：
- 建议采用“复杂度感知路由”：轻量规则留链上，复杂决策图下链执行并链上确认。
- 当前实验的经验阈值：当预估链上 gas 超过约 40~50 万时，链下路径通常更有优势。
