# Relayer Experiment Lab

## Structure

- `src/contract`: relayer contracts and generated split contracts
- `src/relayer-node`: off-chain relayer workers
- `experiment/scripts`: experiment orchestration scripts
- `experiment/dataset`: dataset and case configuration
- `experiment/report`: generated reports and intermediate deployment metadata

## What this provides

- Two-chain local devnet (Anvil A/B)
- Source contract emits cross-chain tasks
- Target contract enforces whitelist + signature + exactly-once
- Relayer worker listens source events and relays to target
- Correctness experiment outputs JSON + Markdown report

## Quick start

```bash
cd /home/logres/system/Experiment/Current/Relayer
npm install
npm run experiment:correctness:full
```

Outputs:

- `experiment/report/correctness-report.json`
- `experiment/report/CORRECTNESS_REPORT.md`

## Dataset-style full run (with unified export)

Dataset config:

- `experiment/dataset/relayer_experiment_dataset.json`

One-click:

```bash
cd /home/logres/system/Experiment/Current/Relayer
npm install
npm run experiment:relayer:full
```

Outputs:

- `experiment/report/RELAYER_UNIFIED_EXPERIMENT_REPORT.md`
- `experiment/report/relayer-unified-report.json`
- `experiment/report/LATENCY_FULL_VS_SPLIT_REPORT.md`
- `experiment/report/latency-full-vs-split-report.json`
- `experiment/report/CORRECTNESS_SPLIT_LATENCY_REPORT.md`
- `experiment/report/FAULT_RECOVERY_REPORT.md`

## Manual commands

```bash
npm run chain:up
npm run compile
npm run deploy
npm run relayer:start
npm run experiment:correctness
npm run chain:down
```
