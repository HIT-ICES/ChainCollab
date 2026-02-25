# Src Governance Baseline

## Purpose

Establish a stable baseline for cleaning and converging `src/` without breaking runtime behavior.

## Current Layering

1. **Platform (runtime-critical)**
   - `backend`, `front`, `agent`, `deployment`, `runtime`
2. **Oracle / chain integration**
   - `oracle` (backend-integrated scripts, preferred)
   - `oracle-node` (parallel stack, needs ownership decision)
   - `oracle-data-compute-lab` (experiment-only)
3. **Modeling / generation**
   - `newTranslator`, `bpmn-chor-app`, `jsoncodeeditor`
4. **Relay / cross-chain experiments**
   - `crosschain-relay-lab`, `relayer-node`, `crosschain_adapter`
5. **Chain runtime artifacts**
   - `geth-node`, `geth_identity_contract`

## Convergence Priorities

1. **Choose one canonical relay path**
   - Keep one of: `crosschain-relay-lab` / `relayer-node` / `crosschain_adapter`.
2. **Choose one canonical oracle control path**
   - Keep `oracle` as backend-integrated source of truth.
   - Mark `oracle-node` as experimental or merge required scripts.
3. **Keep generated/runtime state out of source decisions**
   - `runtime/` should stay operational logs/state only.

## Tooling

Use:

```bash
./src/devtools.sh inspect-src
./src/devtools.sh inspect-src --json --write ./src/runtime/src-inventory.json
./src/devtools.sh governance-check
```

This command provides a module inventory (category, stack hints, compose usage, notes) for governance and refactor planning.

Machine-readable ownership/source-of-truth is defined in:

- [src-module-manifest.json](/home/logres/system/src/docs/src-module-manifest.json)

`governance-check` will detect:

1. Top-level folders not registered in manifest.
2. Manifest entries missing on disk.
3. Multiple `active` modules mapped to the same domain (ownership conflict).
