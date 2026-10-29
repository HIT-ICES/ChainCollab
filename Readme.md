# ChainCollab

ChainCollab supports collaborative business processes modeled with BPMN choreography and DMN. It provides modeling, organization and consortium management, Fabric/Geth environment management, Go/Solidity code generation, and execution of messages, decisions, and cross-chain calls.

The `release-MultiBlockchain` branch contains application source, generation templates, deployment resources, examples, and the original release experiment directory. **Run all commands from the repository root**, unless a command explicitly changes directories. Use the startup entry point below; earlier terminal aliases and legacy translator tutorials are no longer the startup guide.

## 1. Branches and existing installations

The complete pre-cleanup implementation is preserved on `dev-MultiBlockchain` and `dev-MultiBlockChain-fork`. Both preserve the same runnable baseline based on release commit `eaea6028`, including the existing frontend lockfile and database migration previously excluded by ignore rules. Their earlier histories are retained. These development branches also retain manuscript evidence archives and the editor development project. Release retains `Experiment/` with its original layout and contents.

Before switching from release to a development branch, run `python3 scripts/chaincollab.py down`, switch branches, and follow that branch's startup instructions. Existing databases and dependency environments remain on the machine.

```bash
git switch release-MultiBlockchain
# To use the preserved development implementation:
# git switch dev-MultiBlockchain
# or git switch dev-MultiBlockChain-fork
```

Preserving an installation means retaining its code and leaving local virtual environments, `node_modules`, databases, blockchain data, and configuration in place. Git branches do not contain running containers, database contents, or passwords. Private configuration and database backups made during cleanup are stored locally under `.git/release-preservation-20261029/` and are not distributed.

## 2. Prerequisites

The recommended environment is Ubuntu 22.04 or WSL2, Python **3.10**, Node.js **22** (minimum 20.19), Docker Engine, and `docker compose`. Local verification used Node 22.21.0, Go 1.22.0, and FireFly CLI 1.4.0. See the [verification report](docs/RELEASE_VERIFICATION.md) for completed checks and their limits.

For WSL2, start Docker Desktop on Windows and enable Ubuntu under Settings → Resources → WSL Integration. Both commands must succeed:

```bash
docker info
docker compose version
```

If Node.js 12 or 16 is still selected, switch versions first. With nvm installed:

```bash
source "$HOME/.nvm/nvm.sh"
nvm install 22
nvm use 22
```

Install the build tools and Graphviz development libraries required by the Python dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3.10-venv python3.10-dev build-essential pkg-config libgraphviz-dev graphviz libpq-dev
```

The web application uses a packaged modeler and does not require rebuilding its development project. Provisioning blockchain/FireFly environments additionally requires Go, the FireFly CLI, and corresponding container images. Ensure the tools are available on `PATH`; for their usual installation locations:

```bash
export PATH="/usr/local/go/bin:$HOME/go/bin:$PATH"
go version
ff version
```

## 3. Installation and configuration

```bash
git clone --branch release-MultiBlockchain https://github.com/HIT-ICES/ChainCollab.git
cd ChainCollab
python3 scripts/chaincollab.py setup
python3 scripts/chaincollab.py doctor
```

For an existing checkout, run only the final two commands. The `setup` command:

- Preserves existing `.venv` / `venv` directories and local configuration. Healthy environments are reused.
- Creates missing Python 3.10 environments and installs captured dependency versions from each component's `requirements.release.txt`. After an interrupted download, rerun `setup` to complete missing dependencies.
- Registers the B2CDSL, Go, and Solidity packages as editable installations when needed.
- Runs `npm ci` when frontend dependencies need installation. The modeler is installed from `src/front/vendor/bpmn-chor-app-0.1.2.tgz`; a separate editor source server is not required.

Configuration files:

| File | Purpose |
| --- | --- |
| `src/backend/.env` | Django, PostgreSQL, Redis, and media paths; initialized from `.env.example` |
| `src/front/.env.local` | Backend and translator URLs; initialized from `.env.example` |
| `src/backend/docker-compose.yml` | PostgreSQL and Redis services |

The backend reads `src/backend/.env`. Set `WEBROOT=/api/v1`; an older `/api` setting must be updated to match the frontend. Database names, usernames, and passwords must match the Compose `POSTGRES_*` settings. The frontend reads `VITE_BACKEND_URL`, `VITE_TRANSLATOR_URL`, and `VITE_HOST_BASE_URL`. These URLs are accessed by the browser, so use addresses reachable from the browser rather than container-internal hostnames.

**Use a PostgreSQL image compatible with an existing data directory.** The preserved local installation has `pgdata/PG_VERSION` equal to 11, so release defaults to `postgres:11.1`. Cleanup did not upgrade PostgreSQL or recreate its data directory. Other existing installations should select an image matching their own data format; a major-version upgrade requires a separate migration.

Use `POSTGRES_IMAGE` and `REDIS_IMAGE` to override image sources when necessary. Local verification used `public.ecr.aws/docker/library/redis:7` through a private `.env` override; the release default remains unchanged. If an image download returns EOF or times out, restore registry access or select an accessible image source before starting services.

## 4. Starting, stopping, and inspecting services

```bash
python3 scripts/chaincollab.py up
python3 scripts/chaincollab.py status
```

The startup sequence is PostgreSQL/Redis → readiness checks → **committed** database migrations → translator → Docker agent → Celery worker → Django → frontend. Normal startup does not run `makemigrations` or clear the database.

| Service | Default address | Log |
| --- | --- | --- |
| Frontend | http://127.0.0.1:3000 | `.runtime/front.log` |
| Django API | http://127.0.0.1:8000 | `.runtime/backend.log` |
| Translator and API documentation | http://127.0.0.1:9999/docs | `.runtime/translator.log` |
| Docker agent | http://127.0.0.1:7001 | `.runtime/agent.log` |
| Celery worker | Background queue using Redis | `.runtime/worker.log` |

```bash
# Follow the backend log.
tail -f .runtime/backend.log
# Stop managed application processes; databases remain running.
python3 scripts/chaincollab.py down
# Stop database containers without deleting their volumes.
python3 scripts/chaincollab.py db-stop
```

The script manages recorded processes and checks their identities. It does not take over or terminate unrelated processes using the same ports. Resolve reported port conflicts before restarting.

To run individual components in the foreground for diagnosis:

```bash
python3 scripts/chaincollab.py run translator
python3 scripts/chaincollab.py run backend
```

Use `up --no-db` when external database services are already configured and ready. Use `--no-migrate` only when the database schema has already been migrated. To start selected frontend/translation components without database startup or migration:

```bash
python3 scripts/chaincollab.py up --services translator agent front --no-db --no-migrate
```

This starts only the selected components. It does not provision or reproduce a complete blockchain workflow.

## 5. Running a collaborative workflow

For a new installation, create an administrator account if needed. Avoid reinitializing test data in an existing database.

```bash
python3 scripts/chaincollab.py manage createsuperuser
```

Open the frontend, register or sign in, create an organization and consortium, and invite participating organizations or members. Select Fabric or Geth to create an environment, then follow the interface to initialize nodes, networks, and FireFly. Before deployment, verify that required images are accessible, Docker networking is configured, and Go and `ff` are available.

Import `examples/bpmn-dmn/SupplyChainPaper.bpmn` and its companion `supplyChainPaper.dmn`, assign participants, generate and deploy code, create an instance, and execute its message, gateway, and decision nodes.

Code generation does not establish a runtime DMN service binding. Configure bindings using the decision IDs in the actual DMN file. Messages follow Send → wait for receipt confirmation → Complete → completion. BusinessRule tasks follow Request → wait for a result → Continue → output writeback and completion. See the [message confirmation protocol](docs/Solidity_Message_Confirmation.md).

Oracle, DMN/OCR, and Relayer services are separate components required for decision execution or cross-chain calls. Their commands, external prerequisites, and active paths are documented in the [Oracle and Relayer setup guide](docs/ORACLE_RELAYER_SETUP.md). Provision the required blockchain environment before using them.

## 6. Standalone BPMN → PIM → Go / Solidity generation

The following workflow does not require a database, frontend, or blockchain node:

```bash
mkdir -p .runtime/generated/go .runtime/generated/solidity
src/newTranslator/.venv/bin/python src/newTranslator/generator/bpmn_to_dsl.py \
  examples/bpmn-dmn/SupplyChainPaper.bpmn \
  -o .runtime/generated/SupplyChainPaper.b2c -n SupplyChainPaper
src/newTranslator/.venv/bin/textx generate .runtime/generated/SupplyChainPaper.b2c \
  --target go --output-path .runtime/generated/go --overwrite
src/newTranslator/.venv/bin/textx generate .runtime/generated/SupplyChainPaper.b2c \
  --target solidity --output-path .runtime/generated/solidity --overwrite
```

These commands use the implemented parser, textX grammar, and Jinja templates. They generate the B2CDSL representation and target code; no separate PSM file is exported. The companion DMN file is not evaluated during this generation step.

Run source checks and build the frontend with:

```bash
python3 scripts/chaincollab.py check
# Build the frontend for production.
(cd src/front && npm run build)
```

## 7. Repository layout and experiment materials

```text
Experiment/                     Original release experiment models, scripts, and results
examples/bpmn-dmn/               Structured BPMN/DMN inputs for the generation example
scripts/chaincollab.py           Shared setup / doctor / up / down / check entry point
src/backend/                    Django, migrations, and blockchain deployment resources
src/agent/docker-rest-agent/     Docker resource connector
src/front/                      Main frontend and packaged modeler
src/newTranslator/              Parser, DSL, Jinja generators, API, and tests
src/oracle/                     Oracle / OCR / DMN components used by the backend
src/relayer-node/                Cross-chain relaying service and optional interface
src/geth_identity_contract/      Participant identity contract for Geth instances
docs/                           Release scope, operating guides, and verification records
```

`Experiment/` retains all 3,631 files from the pre-cleanup release under `BPMNwithDMNcase/`, `NoiseExperiment/`, `PerformanceTest/`, and `new/`. The structured SupplyChainPaper model is at `Experiment/BPMNwithDMNcase/new/SupplyChainPaper.bpmn`. Use `examples/bpmn-dmn/` for the standalone generation walkthrough; the original experiment layout and recorded data remain under `Experiment/`. Repository cleanup did not rerun experiments or rewrite their results.

The [release scope record](docs/RELEASE_LAYOUT.md) explains which development materials remain on development branches. `.gitignore` excludes retained local development directories, virtual environments, `node_modules`, configuration, and runtime data from new release checkouts.

## 8. Troubleshooting

- **Unsupported Node version:** select the required version with nvm and rerun `doctor`.
- **Docker API unavailable:** start Docker Desktop/Engine and check WSL integration and `docker context show`.
- **Image download EOF or timeout:** check registry connectivity or configure accessible `POSTGRES_IMAGE` / `REDIS_IMAGE` sources.
- **PostgreSQL data directory version mismatch:** select the image major version matching `PG_VERSION`; retain the existing data directory.
- **Missing B2CDSL packages:** use the translator's Python environment to install its three local packages with `pip install -e`.
- **Blockchain provisioning fails:** inspect `.runtime/backend.log`, agent logs, image availability, Go/FireFly executables, and the target environment's hosts and Docker network configuration. An accessible frontend alone does not establish that blockchain provisioning succeeded.
- **Oracle or Relayer offline:** follow the optional-component guide and check node URLs, runtime identities, and job/contract configuration.
