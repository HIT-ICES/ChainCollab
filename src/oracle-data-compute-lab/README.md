# Oracle Data + Compute Lab

This folder implements a standalone mechanism for:
- External data on-chain (`external-data`): request data from off-chain source and anchor it into on-chain slots.
- Compute task off-chain (`compute-task`): request computation based on on-chain slots, execute off-chain, write result back on-chain.
- Gas experiments: measure gas for request and fulfill transactions.

## Architecture

- `contracts/SlotRegistry.sol`
  - Global shared state slots: `bytes32 slotKey -> string value`.
  - Authorizes writer contracts.
- `contracts/DataOracleHub.sol`
  - Handles external-data tasks only.
  - Relayer fulfills task and writes into `SlotRegistry`.
- `contracts/ComputeOracleHub.sol`
  - Handles compute-task tasks only.
  - Relayer computes result and writes into `SlotRegistry`.
- `contracts/DataAggregationLab.sol`
  - Multi-oracle submissions with methods: `MEAN`, `MEDIAN`, `TRIMMED_MEAN`, `WEIGHTED_MEAN`.
  - Final aggregated value anchored into `SlotRegistry`.
- `contracts/ComputeCostLab.sol`
  - On-chain compute benchmark contract for direct vs heavy compute gas comparison.
- `scripts/worker.js`
  - Off-chain listener/processor for both hubs.
  - Fetches external source JSON, executes compute task DSL, writes back via corresponding hub.
- `scripts/compute-task-executor.js`
  - Compute task language parser/executor (safe, no `eval/new Function`).
  - Supports DSL + legacy numeric expression compatibility.
- `scripts/experiment-gas.js`
  - Runs split-contract end-to-end flow and writes gas report to `deployments/gas-report.json`.
- `scripts/experiment-aggregation.js`
  - Tests aggregation consistency / robustness / cost and writes `deployments/aggregation-report.json`.
- `scripts/experiment-compute-cost.js`
  - Compares off-chain compute path vs on-chain compute path and writes `deployments/compute-cost-report.json`.

## Why this design

- Keeps your core project untouched by putting all code under one independent folder.
- Uses event-driven relay model, same pattern as Chainlink-style off-chain execution.
- Maintains explicit slot-based state space so BPMN/DSL can map task outputs to shared state.
- Explicitly separates data oracle path and compute oracle path while preserving shared slot interaction.

## Run (Hardhat local chain)

Terminal 1:
```bash
cd /home/logres/system/src/oracle-data-compute-lab
npm install
npm run node
```

Terminal 2:
```bash
cd /home/logres/system/src/oracle-data-compute-lab
npm run build
npm run deploy
```

Terminal 3 (mock external data source):
```bash
cd /home/logres/system/src/oracle-data-compute-lab
npm run mock
```

Terminal 4 (continuous off-chain worker):
```bash
cd /home/logres/system/src/oracle-data-compute-lab
npm run worker
```

## Gas experiment

Run this after node + mock are up:
```bash
cd /home/logres/system/src/oracle-data-compute-lab
npm run experiment:gas
```

Output:
- Console table with gas usage for each step.
- `deployments/gas-report.json` with full tx hashes and final slot values.

## Aggregation experiment (consistency / robustness / cost)

```bash
cd /home/logres/system/src/oracle-data-compute-lab
npm run experiment:aggregation
```

Output:
- `deployments/aggregation-report.json`
- Per method (`MEAN`/`MEDIAN`/`TRIMMED_MEAN`/`WEIGHTED_MEAN`) metrics:
  - `mae` (accuracy),
  - `stddev` (consistency),
  - `maeIncrease` under outliers (robustness),
  - `avgTotalGas` (cost).

## Compute cost experiment (off-chain vs on-chain)

```bash
cd /home/logres/system/src/oracle-data-compute-lab
npm run experiment:compute-cost
```

Output:
- `deployments/compute-cost-report.json`
- Metrics:
  - off-chain path: `requestComputeTask + fulfillComputeTask` gas + local CPU time
  - on-chain direct compute gas
  - on-chain heavy compute gas (`HEAVY_LOOPS`, default `600`)

## Compute Task DSL

`requestComputeTask` third-party payload now supports two forms:
- DSL (recommended): `dsl:<json>`
- JS sandbox task: `js:<code or json>`
- Legacy numeric expression (compat): e.g. `(x0 * 0.2) + (x1 * 0.00001)`

Input aliases are still based on order in `inputSlotKeys`: `x0`, `x1`, `x2`, ...

DSL schema (v1):
```json
{
  "version": "compute-dsl/v1",
  "kind": "numeric",
  "cast": "number",
  "expr": {
    "op": "add",
    "args": [
      { "op": "mul", "args": [{ "var": "x0" }, { "const": 0.2 }] },
      { "op": "mul", "args": [{ "var": "x1" }, { "const": 0.00001 }] }
    ]
  }
}
```

Supported task families:
- Numeric compute: `add/sub/mul/div/pow/mod/min/max/avg/median/stddev/weighted_mean`
- Rule/decision: `gt/gte/lt/lte/eq/neq/and/or/not/if/clamp`
- Transformation: `round/floor/ceil/abs/concat/number/string/bool/list/object`

Worker converts execution result into chain string (`toChainString`) before `fulfillComputeTask`.

### JS mode (experimental)

JS mode is executed by Node `vm` sandbox with timeout and no dynamic codegen.

Short form:
```text
js:return (x0 * 2 + x1) / 10;
```

JSON form:
```json
{
  "engine": "js",
  "version": "compute-js/v1",
  "cast": "number",
  "timeoutMs": 400,
  "code": "const score = helpers.weightedMean([x0, x1], [0.3, 0.7]); return helpers.round(score, 2);"
}
```

Available helper methods:
- `helpers.mean(array)`
- `helpers.median(array)`
- `helpers.stddev(array)`
- `helpers.weightedMean(values, weights)`
- `helpers.clamp(value, lo, hi)`
- `helpers.toNumber(value, label?)`
- `helpers.round(value, digits?)`

Recommended usage:
- production/research reproducibility: DSL
- fast prototyping: JS mode

## Optional simulator

You can use Anvil instead of Hardhat node by setting:
```bash
ANVIL_RPC_URL=http://127.0.0.1:8545
```
and switching network when running deploy/experiment commands.
