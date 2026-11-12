# Release scope and preservation

The cleanup baseline is `eaea602845b57af10e45c9f434d6557bed4a7f67`.
Before cleanup, `dev-MultiBlockchain` and `dev-MultiBlockChain-fork` were given
the **same complete Git tree** based on this baseline, including the existing
API migration and frontend lock previously excluded by ignore rules, using merge commits that preserve their
prior histories. Backup refs are under `backup/pre-release-cleanup-20261029/`.
These development branches retain the complete baseline, archives and developer tools.
Release groups the verification materials under `Experiment/verification/` and the timing workloads under `Experiment/PerformanceTest/`. See the [experiment index](../Experiment/README.md).

| Path | Release decision | Reason |
| --- | --- | --- |
| `src/backend`, `src/agent/docker-rest-agent`, `src/front` | Keep | Main control plane and Docker connector |
| `src/newTranslator` core, grammar, templates and tests | Keep | Active Go/Solidity generator called by the backend |
| `src/bpmn-chor-app` development project | Development branches | Frontend uses its packaged library, not its source server |
| `src/front/vendor/bpmn-chor-app-0.1.2.tgz` | Keep | Packaged editor from dev, with its checksum pinned in the release lockfile |
| `src/oracle/CHAINLINK`, `src/oracle/03-ocr-multinode`, `src/oracle/04-dmn-ocr` | Keep | All participate in the backend's Oracle/OCR setup chain |
| `src/oracle-node` | Development branches | Parallel old stack; active backend resolves `src/oracle` |
| `src/relayer-node` | Keep | Active backend exposes status/control endpoints for this service |
| `src/py_translator` | Local/development only | Already untracked; backend uses newTranslator |
| `src/java-env-custom-image` | Local/development only | Existing separate Git repository; never deleted or incorporated |
| `Experiment` | Keep and extend | Verification evidence, path perturbation, and four RQ5 workloads, with deployment-specific live configurations kept locally |
| `src/newTranslator/MDAcheck` | Keep selected files | Ecore, OCL, validation runner, and eleven DSL inputs used by the experiment checkers |
| `artifacts`, manuscript evidence and old tutorials | Development branches | Evidence archives and retired development documentation |
| `Experiment/BPMNwithDMNcase` | Keep | Canonical structured BPMN/DMN examples |
| `Experiment/verification/fixtures` | Keep | Eleven historical BPMN inputs for the archived RQ1B and RQ1C runs |
| Other MDAcheck datasets, newTranslator build/dashboard and standalone developer dashboards | Development branches | Additional generated outputs or duplicate development interfaces |
| Existing environments, pgdata, .env, credentials and runtime directories | Preserve locally, ignore in Git | Machine state is not release source |

The active Oracle/OCR directories cannot be removed merely because they resemble
development folders. `run-setup-lite.sh` explicitly needs the forked
`src/oracle/03-ocr-multinode`, in addition to `CHAINLINK` and `04-dmn-ocr`.

This release keeps one operational entry point: `scripts/chaincollab.py`.
`scripts/ctl.sh` and `src/devtools.sh` forward to it for compatibility.
`Readme.md` is the authoritative startup guide. No second checkout/worktree is
created by the release tooling.
