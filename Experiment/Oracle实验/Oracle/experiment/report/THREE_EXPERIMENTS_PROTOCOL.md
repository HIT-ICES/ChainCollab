# Three-Experiment Protocol

## E1. Overall Byzantine Tolerance (Data + Compute)

- Script: `scripts/experiment-overall-bft.js`
- Malicious ratios: `0, 0.2, 0.4`
- Data strategies: `MEAN, MEDIAN, WEIGHTED_MEAN, TRIMMED_MEAN`
- Compute strategies: `FIRST_RESPONSE, MAJORITY, STRICT_ALL`
- Core outputs:
  - Data success rate under tolerance
  - Compute finalize rate / correctness rate
  - Combined overall score

## E2. Data Aggregation Effectiveness

- Script: `scripts/experiment-data-aggregation-benchmark.js`
- Dataset: `datasets/stock_price_scenarios.json`
- Metrics:
  - MAE / RMSE / stddev
  - Success rate under tolerance
  - Avg total gas
  - Robustness degradation across malicious ratios
- References included in output JSON:
  - Yin et al. (ICML 2018)
  - Blanchard et al. (NIPS 2017)
  - Chainlink data feed architecture

## E3. Compute 10 Scenarios Cost Comparison

- Script: `scripts/experiment-compute-10-scenarios.js`
- Dataset: `datasets/compute_tasks_10_scenarios.json`
- Compare:
  - On-chain direct compute
  - Oracle off-chain compute + on-chain finalize
- Metrics:
  - `directGas`
  - `offchainGas`
  - `optimizationPercent`
  - scenario-level and category-level summary
