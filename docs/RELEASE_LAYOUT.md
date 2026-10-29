# Release scope and preservation

The cleanup baseline is `eaea602845b57af10e45c9f434d6557bed4a7f67`.
Before cleanup, `dev-MultiBlockchain` and `dev-MultiBlockChain-fork` were given
the **same complete Git tree** based on this baseline, including the existing
API migration and frontend lock previously excluded by ignore rules, using merge commits that preserve their
prior histories. Backup refs are under `backup/pre-release-cleanup-20261029/`.
These development branches retain experiments, archives and developer tools.

| Path | Release decision | Reason |
| --- | --- | --- |
| `src/backend`, `src/agent/docker-rest-agent`, `src/front` | Keep | Main control plane and Docker connector |
| `src/newTranslator` core, grammar, templates and tests | Keep | Active Go/Solidity generator called by the backend |
| `src/bpmn-chor-app` development project | Development branches | Frontend uses its packaged library, not its source server |
| `src/front/vendor/bpmn-chor-app-0.1.2.tgz` | Keep | Same original archive bytes; installable by npm in a clean checkout |
| `src/oracle/CHAINLINK`, `src/oracle/03-ocr-multinode`, `src/oracle/04-dmn-ocr` | Keep | All participate in the backend's Oracle/OCR setup chain |
| `src/oracle-node` | Development branches | Parallel old stack; active backend resolves `src/oracle` |
| `src/relayer-node` | Keep | Active backend exposes status/control endpoints for this service |
| `src/py_translator` | Local/development only | Already untracked; backend uses newTranslator |
| `src/java-env-custom-image` | Local/development only | Existing separate Git repository; never deleted or incorporated |
| `Experiment`, `artifacts`, manuscript evidence and old tutorials | Development branches | Not needed to launch the system |
| `examples/bpmn-dmn` | Keep | Structured BPMN/DMN inputs for reproduction |
| newTranslator MDAcheck/build/dashboard and standalone developer dashboards | Development branches | Generated outputs or duplicate development interfaces |
| Existing environments, pgdata, .env, credentials and runtime directories | Preserve locally, ignore in Git | Machine state is not release source |

The active Oracle/OCR directories cannot be removed merely because they resemble
development folders. `run-setup-lite.sh` explicitly needs the forked
`src/oracle/03-ocr-multinode`, in addition to `CHAINLINK` and `04-dmn-ocr`.

This release keeps one operational entry point: `scripts/chaincollab.py`.
`scripts/ctl.sh` and `src/devtools.sh` forward to it for compatibility.
`Readme.md` is the authoritative startup guide. No second checkout/worktree is
created by the release tooling.
