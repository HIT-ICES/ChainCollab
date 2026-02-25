# Oracle Task Suite (MainRouter + DataAdapter + ComputeAdapter)

This suite introduces three contracts:

1. `MainOracleRouter`  
   Accepts business requests on-chain and dispatches them to task adapters.
2. `ChainlinkDataTaskAdapter`  
   Triggers Chainlink data tasks and reports results back to `MainOracleRouter`.
3. `ChainlinkComputeTaskAdapter`  
   Triggers Chainlink compute tasks and reports results back to `MainOracleRouter`.

## Files

- Contracts:
  - `contracts/MainOracleRouter.sol`
  - `contracts/ChainlinkDataTaskAdapter.sol`
  - `contracts/ChainlinkComputeTaskAdapter.sol`
- Deploy script:
  - `scripts/deploy-oracle-task-suite.js`
- Job templates:
  - `../04-dmn-ocr/job-spec-main-data-task.toml`
  - `../04-dmn-ocr/job-spec-main-compute-task.toml`

## Deploy

```bash
cd src/oracle/CHAINLINK
./compile.sh
node scripts/deploy-chainlink.js
node scripts/deploy-oracle-task-suite.js
```

Optional env:

- `RPC_URL`
- `DEPLOYER_ACCOUNT` / `ETH_SYSTEM_ACCOUNT`
- `DATA_TASK_JOB_ID`
- `COMPUTE_TASK_JOB_ID`
- `ORACLE_TASK_FEE_WEI`
- `CHAINLINK_NODE_ADDRESS`

Deploy output:

- `deployment/oracle-task-suite.json`

## Runtime flow

1. Client calls `MainOracleRouter.requestData(...)` or `requestCompute(...)`.
2. Router forwards call to the corresponding adapter.
3. Adapter sends Chainlink request (`OracleRequest` on Operator).
4. Chainlink job processes data/compute and writes back via:
   - `commitDataFromRaw(...)`, or
   - `commitComputeFromRaw(...)`.
5. Adapter calls router callback:
   - `onDataTaskResult(...)`, or
   - `onComputeTaskResult(...)`.
6. Router marks task completed and stores final raw result on-chain.

## What still needs to be implemented in the full system

1. Backend APIs
   - Create data task / compute task requests.
   - Query task lifecycle (`PENDING`, `COMPLETED`, `FAILED`).
2. Chainlink job management
   - Create/update/delete jobs from backend.
   - Persist job IDs per environment.
3. Frontend interaction
   - Forms for data and compute task requests.
   - Live task status table and result viewer.
4. Experiment framework
   - Multi-node differentiated sources.
   - Pluggable aggregation policy for research benchmarks.
5. Reliability
   - Timeout and retry policy.
   - Fallback writer / dead-letter handling.
