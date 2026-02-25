# Control Plane Ops

## Core Stack Commands

From repo root:

```bash
./src/devtools.sh up --profile core
./src/devtools.sh up --profile research
./src/devtools.sh status
./src/devtools.sh down
./src/devtools.sh restart --profile core
```

`up/restart` runs `governance-check` by default.
To bypass once:

```bash
./src/devtools.sh up --profile core --skip-governance-check
```

### What `status` checks

1. PID file entries (`src/runtime/devtools.pids`)
2. Process liveness (`os.kill(pid, 0)`)
3. Port occupancy for core services:
   - newTranslator: `9999`
   - agent: `7001`
   - backend: `8000`
   - front: `3000`
4. Runtime task log count (`src/runtime/tasks/task-*.log`)

## Governance Commands

```bash
./src/devtools.sh inspect-src
./src/devtools.sh inspect-src --json --write ./src/runtime/src-inventory.json
./src/devtools.sh governance-check
```

## Commit / CI Integration

Install local git hooks:

```bash
./src/scripts/install_git_hooks.sh
```

This installs:

- `pre-commit`: runs `./src/devtools.sh governance-check`

CI workflow:

- [.github/workflows/src-governance-check.yml](/home/logres/system/.github/workflows/src-governance-check.yml)
- Runs `python3 ./src/scripts/governance_check.py` on push and pull_request.

`governance-check` validates:

1. New top-level folders are registered in manifest.
2. Manifest entries still exist on disk.
3. No multi-owner conflict for `active` domains.

Manifest file:

- [src-module-manifest.json](/home/logres/system/src/docs/src-module-manifest.json)

## Recommended Daily Flow

1. `./src/devtools.sh governance-check`
2. `./src/devtools.sh status`
3. Start/stop as needed (`up` / `down`)
4. For large refactors, snapshot inventory:
   - `./src/devtools.sh inspect-src --json --write ./src/runtime/src-inventory.json`
