# Oracle Data/Compute Split-Contract Experiment Report

## 1. Objective

This report summarizes two independent oracle experiments:

1. Data task aggregation experiment: compare multiple aggregation methods under clean vs outlier scenarios.
2. Compute task off-chain execution experiment: compare on-chain compute cost vs off-chain compute + on-chain commit cost.

The implementation uses split contracts:

- `DataAggregationLab` (data task)
- `ComputeCostLab` (compute task)

---

## 2. Experiment Setup

### 2.1 Environment

- Local EVM test network (Hardhat)
- Solidity contracts deployed from `src/oracle-data-compute-lab`
- Result files:
  - `deployments/aggregation-report.json`
  - `deployments/compute-cost-report.json`
  - `deployments/separate-analysis-report.json`

### 2.2 Data Task Design

- Rounds: `12`
- Reference true value: `1000`
- Scenarios `n=2`:
  - `clean` (low-noise observations)
  - `outlier` (contains abnormal observations)
- Aggregation methods `m=4`:
  - `MEAN`
  - `MEDIAN`
  - `TRIMMED_MEAN`
  - `WEIGHTED_MEAN`

This yields `n*m = 2*4 = 8` result groups.

### 2.3 Compute Task Design

- Rounds: `15`
- Input: `x0=2500`, `x1=50000`
- DSL expression:

```text
dsl:{"version":"compute-dsl/v1","kind":"numeric","cast":"number","expr":{"op":"div","args":[{"op":"add","args":[{"op":"mul","args":[{"var":"x0"},{"const":2}]},{"var":"x1"}]},{"const":10}]}}
```

- Comparison targets:
  - Off-chain execution + on-chain fulfill
  - On-chain direct lightweight compute
  - On-chain heavy-loop compute (`heavyLoops=600`)

---

## 3. Results

## 3.1 Data Task Aggregation Results

### Clean Scenario

| Method | MAE | Stddev | Avg Total Gas |
|---|---:|---:|---:|
| MEAN | 0.9167 | 0.9538 | 907,273.5 |
| MEDIAN | 2.8333 | 2.6874 | 909,984.0 |
| TRIMMED_MEAN | 1.3333 | 1.6330 | 911,689.5 |
| WEIGHTED_MEAN | 2.2500 | 1.8911 | 920,025.0 |

### Outlier Scenario

| Method | MAE | Stddev | Avg Total Gas |
|---|---:|---:|---:|
| MEAN | 54.0000 | 62.0504 | 905,950.5 |
| MEDIAN | 24.1667 | 69.0187 | 909,773.5 |
| TRIMMED_MEAN | 43.0833 | 68.2183 | 911,343.0 |
| WEIGHTED_MEAN | 39.6667 | 52.2914 | 920,122.0 |

### Robustness (Outlier MAE increase vs Clean)

| Method | MAE Increase | Ratio |
|---|---:|---:|
| MEAN | 53.0833 | 58.9091x |
| MEDIAN | 21.3333 | 8.5294x |
| TRIMMED_MEAN | 41.7500 | 32.3125x |
| WEIGHTED_MEAN | 37.4167 | 17.6296x |

### Data Task Summary

- Best clean accuracy: `MEAN`
- Best outlier accuracy: `MEDIAN`
- Best robustness: `MEDIAN`
- Best gas efficiency: `MEAN`

---

## 3.2 Compute Task Cost Results

| Metric | Value |
|---|---:|
| Off-chain avg request gas | 305,584.6 |
| Off-chain avg fulfill gas | 113,138.2 |
| Off-chain avg total gas | 418,722.8 |
| Off-chain avg CPU time | 0.0687 ms |
| On-chain avg direct gas | 27,428.67 |
| On-chain avg heavy gas | 240,363.67 |

Derived ratios:

- Off-chain / On-chain Direct = `15.27x`
- Off-chain / On-chain Heavy = `1.74x`

---

## 4. Analysis

## 4.1 Data Task

1. In low-noise settings, `MEAN` gives best accuracy and lowest gas.
2. Under outliers, `MEDIAN` shows clearly better robustness (lowest MAE increase).
3. `TRIMMED_MEAN` and `WEIGHTED_MEAN` are intermediate choices; they may require better tuning (trim ratio, weights) for stronger robustness/efficiency trade-offs.

## 4.2 Compute Task

1. For lightweight deterministic formulas, direct on-chain compute remains much cheaper in gas.
2. For heavier compute, the gap narrows, but off-chain path still costs more in this setup.
3. Off-chain route provides flexibility (complex logic, external libraries, dynamic data), while gas advantage depends on reducing callback overhead and batching strategy.

---

## 5. Methodological Backing

The method design aligns with common findings in prior work:

1. Robust statistics:
   - Median/trimmed estimators are less sensitive to outliers than mean in noisy sensing environments.
2. Oracle trust model:
   - Multi-source aggregation is a standard approach to mitigate single-source manipulation.
3. Blockchain cost model:
   - On-chain arithmetic is usually cheaper for simple formulas, while off-chain compute is justified for complex logic and external-data dependencies.

---

## 6. Threats to Validity

1. Current scenarios are synthetic (`clean/outlier`) and should be extended to real IIoT datasets.
2. Compute workload diversity is still limited (single DSL expression family).
3. Gas results depend on chain configuration and callback design.

---

## 7. Next Experimental Extensions

1. Expand data scenarios from `n=2` to `n>=4` (e.g., energy, predictive maintenance, quality control, anomaly detection).
2. Add adaptive weighted aggregation and confidence-aware trimming.
3. Add multiple compute workloads (FFT-like numeric loop, rule engine, matrix op, anomaly score) and compare:
   - on-chain direct
   - off-chain + callback
   - off-chain batched callback

