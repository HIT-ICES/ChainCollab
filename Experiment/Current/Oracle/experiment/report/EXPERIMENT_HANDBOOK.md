# Oracle 实验手册

本手册用于统一说明 `Experiment/Oracle` 目录下的实验方案、数据集与执行指令。

## 1. 实验设计总览

当前实验分为 4 条主线：

1. 数据聚合有效性实验（工业数据，无恶意节点）
2. 计算任务成本实验（链上直算 vs 链下计算回传）
3. DMN 复杂决策任务成本实验
4. 安全性实验（白名单 + 结果签名，对抗越权/伪造/重放）

### 1.1 数据聚合有效性实验

- 目标：验证 MEAN / MEDIAN / WEIGHTED_MEAN / TRIMMED_MEAN 在真实工业数据质量问题下的效果差异。
- 问题类型：传感器噪声、校准漂移、缺失与陈旧数据。
- 指标：`MAE / RMSE / MAPE`，并统计各场景最优聚合算法。

### 1.2 计算任务成本实验

- 目标：量化“直接链上计算”与“链下计算+链上提交结果”之间的 Gas 差异。
- 任务类型：数值计算、逻辑判断、混合任务。
- 输出：每个任务的表达式、两种路径成本、优化比例。

### 1.3 DMN 复杂决策成本实验

- 目标：衡量复杂规则决策在链上执行的成本增长趋势，并与链下执行模式对比。
- 场景：工业互联网中的多条件判断、规则组合、决策表复杂度上升。

### 1.4 白名单+签名安全实验

- 目标：验证以下机制的抗攻击有效性：
  - 任务级白名单（allowed oracles）
  - 结果签名绑定（taskId + payload/result + signer）
- 攻击向量：
  - outsider submission
  - registered but not allowed
  - signature forgery / sender mismatch
  - tampered payload
  - replay (same-task / cross-task)
  - post-finalize submission
  - batch with outsider signature（compute）

## 2. 实验数据集（描述与位置）

### 2.1 工业数据聚合数据集

- 文件：`datasets/industrial_data_aggregation_scenarios.json`
- 生成脚本：`scripts/prepare-industrial-data-aggregation.py`
- 来源：UCI 工业相关数据（自动采集并加工为场景化输入）
- 用途：数据聚合有效性实验

### 2.2 10 场景计算任务数据集

- 文件：`datasets/compute_tasks_10_scenarios.json`
- 用途：链上直算 vs 链下计算成本实验（主报告）
- 内容：任务名称、类型、表达式/语义、输入参数等

### 2.3 DMN 复杂决策案例集

- 文件：`datasets/dmn_compute_cases.json`
- 用途：DMN 决策复杂度成本实验

### 2.4 其他辅助数据集

- `datasets/stock_price_scenarios.json`：历史数据聚合/鲁棒性基准案例
- `datasets/compute_payloads.json`：整体 BFT/Compute 相关辅助输入

## 3. 实验脚本与执行指令

执行目录：

```bash
cd /home/logres/system/Experiment/Oracle
```

首次准备：

```bash
npm install
npm run compile
```

若要重新采集工业数据：

```bash
python3 -m pip install ucimlrepo
npm run data:prepare-industrial
```

### 3.1 数据聚合有效性实验（工业）

```bash
npm run experiment:data-industrial-report
```

对应流程：

1. `data:prepare-industrial`
2. `experiment:data-industrial`
3. `report:data-industrial`

### 3.2 计算任务成本实验（10 场景）

```bash
npm run experiment:compute-10-scenarios
```

### 3.3 DMN 复杂度实验

```bash
npm run experiment:dmn-complexity
```

### 3.4 统一计算总报告（10 场景 + DMN）

```bash
npm run experiment:compute-unified
```

### 3.5 白名单+签名安全实验

```bash
npm run experiment:security-whitelist-signature
```

### 3.6 三件套实验（历史组合）

```bash
npm run experiment:three
```

## 4. 关键脚本清单

- 数据聚合实验：`scripts/experiment-data-industrial-aggregation.js`
- 工业数据准备：`scripts/prepare-industrial-data-aggregation.py`
- 数据聚合报告生成：`scripts/generate-data-industrial-report.js`
- 计算 10 场景实验：`scripts/experiment-compute-10-scenarios.js`
- DMN 复杂度实验：`scripts/experiment-dmn-complexity.js`
- 统一计算报告：`scripts/generate-compute-unified-report.js`
- 安全性实验：`scripts/experiment-security-whitelist-signature.js`

## 5. 实验输出文件（deployments）

- `deployments/DATA_INDUSTRIAL_AGGREGATION_REPORT.md`
- `deployments/data-industrial-aggregation-report.json`
- `deployments/COMPUTE_10_SCENARIOS_REPORT.md`
- `deployments/compute-10-scenarios-report.json`
- `deployments/DMN_COMPLEXITY_REPORT.md`
- `deployments/dmn-complexity-report.json`
- `deployments/COMPUTE_UNIFIED_EXPERIMENT_REPORT.md`
- `deployments/security-whitelist-signature-report.json`
- `deployments/SECURITY_WHITELIST_SIGNATURE_REPORT.md`

## 6. 最小复现实验路线（推荐）

按以下顺序即可复现你当前论文主线：

1. `npm run experiment:data-industrial-report`
2. `npm run experiment:compute-unified`
3. `npm run experiment:security-whitelist-signature`

该路线分别覆盖：数据聚合效果、计算成本收益、安全机制有效性。
