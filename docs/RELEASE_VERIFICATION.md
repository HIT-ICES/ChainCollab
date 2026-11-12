# Release verification — 2026-10-29

## Section V artifact update — 2026-11-12

The [experiment index](../Experiment/README.md) maps the seven experiment units to their inputs, scripts, and evidence. The release integrates the file-message implementation and timing workloads from dev commit `afaa3e77`. Archived results retain their original contents.

| Check | Outcome |
| --- | --- |
| RQ1A, Eclipse OCL | Validated 450 archived XMI inputs. All 11 positives passed and all 439 negatives produced violations. |
| RQ1B, structural checker | Regenerated reports for the 11 archived source cases. All passed. |
| RQ1C, bounded behavior | Regenerated the 11 case reports and 75 logical paths. All case reports passed. |
| RQ2, Go and Solidity static checks | All 11 cases passed with the current generator and the checker that follows Solidity message completion. |
| RQ3, archived comparisons | All three pairs have 75 consistent comparisons and 1,100 steps per platform. A fresh offline comparison of a SupplyChainPaper trace pair also passed. |
| RQ4, available archive | Counted 6,917 records from the Fabric perturbation runs. The final 6,920-record set and matching Geth archive remain to be located. |
| RQ5, archived timing | All 439 files listed under `results-100` in the paper's transfer manifest matched SHA-256. The four groups contain 100 per-round records each. The Geth BRT verifier replayed 800 stage intervals offline. |
| Application checks | Five file-message service tests, four generator regression tests, Django checks, TypeScript checking, clean dependency installation, and the frontend production build passed. |

The RQ3, RQ4, and RQ5 checks above inspect recorded runs. Repeating live measurements requires the corresponding Fabric/Geth, FireFly, and rule-service deployments.

## Layout update

The structured examples are under `Experiment/BPMNwithDMNcase/`. The seven experiment units are grouped by research question in `Experiment/`. The archived reports retain the paths recorded at the time of each run.

## Original release cleanup

This records repository cleanup and startup verification, not a new research
experiment. Existing benchmark data and live-chain results were not rerun or
rewritten.

## Preserved development state

The original pre-cleanup release commit is `eaea602845b57af10e45c9f434d6557bed4a7f67`.
The complete runnable preservation commit is `cf1e6f75b973eb9e6425cb8ee9d039e40bd9cf9c`, with tree `60cce29876db29750dc9d73598da6f993229a2ed`.
It adds the existing API migration and the frontend dependency lock that were
previously excluded by ignore rules. The development lock retains the original
editor archive location; release relocates only that archive reference.

| Branch | Preserved commit | Tree comparison |
| --- | --- | --- |
| `dev-MultiBlockchain` | `2af831f4003929aa8f5b5bf7b9677fda11d34535` | Exactly equal to the complete preserved release tree |
| `dev-MultiBlockChain-fork` | `4759e58b79f526d34bcc713a4993940c598a6b6f` | Exactly equal to the complete preserved release tree |

Both are merge commits retaining each development branch's previous history.
No force reset, history rewrite, extra worktree, environment removal, database
replacement or chain-data cleanup was used.

Local configuration, original branch refs, the cleanup inventory and a private
pre-migration PostgreSQL dump are retained under
`.git/release-preservation-20261029/`. They are not release files. The original
database used PostgreSQL 11 format; its matching `postgres:11.1` image is retained
and is also the release default. Applying the existing committed migration did
not require generating new migrations.

## Checks completed

| Check | Result |
| --- | --- |
| `setup` against existing environments | Preserved all three existing venvs and local configuration |
| `doctor` | Node 22.21.0, Docker 29.2.1, Compose 5.1.0 and application imports passed; Go 1.22.0 / ff 1.4.0 available |
| Existing Python dependency consistency | Backend, agent and translator: `pip check` all passed |
| Django configuration and migration graph | `manage.py check` passed; `makemigrations --check --dry-run` reported no changes |
| Fresh PostgreSQL schema | Disposable test database created from the retained migrations, 26 migration records; test database removed afterward |
| Full application startup | PostgreSQL, Redis, translator, agent, Celery worker, backend and frontend started with the documented entry point |
| Stop/restart and idempotent start | Managed processes stopped/restarted successfully; already-running managed processes reused |
| Redis / Celery | Redis returned PONG; Celery connected to Redis and reported ready |
| HTTP smoke | Seven checks passed: frontend, Django API docs, agent Docker inventory, translator OpenAPI, BPMN→DSL, DSL→Go, BPMN→Solidity |
| Message lifecycle in generated code | Both HTTP-generated targets contain the expected waiting state and `Message_0rwz1km_Complete` |
| Generator regressions | Four tests passed using existing and clean translator environments |
| Git-only source export | Exported the staged tree, excluding local configs/untracked source; backend check, migration check, clean-dependency frontend build and generator tests all passed; native generated Go/Solidity matched live HTTP outputs byte-for-byte |
| Windows-side HTTP | Frontend and Django docs both returned HTTP 200 from Windows localhost |
| Frontend clean install/build | Independent `npm ci` and production build passed, using the vendored editor archive and no editor development source tree |
| Translator clean install | New isolated Python 3.10 environment installed the release lock plus three editable packages; tests passed |
| Agent clean install | New isolated Python 3.10 environment installed the release lock; imports passed |
| Backend clean install | Not completed: Python package downloads were slow and the first attempt timed out. The optional retry was stopped; the existing backend environment, its complete lock, dependency consistency, configuration, database migrations and live HTTP operation were verified |

Local detailed outputs are under `.release-verification/` and `.runtime/`, both
ignored in Git. They include installation/build logs, HTTP check metadata and
generated example outputs. They are not packaged as research evidence or a
claim of live blockchain execution.

Docker Hub returned EOF during this run. The local Redis image was fetched from
the public official-library mirror, using the documented `REDIS_IMAGE` override.
The fetched digest was
`sha256:b6b6e3dc0c0952737748e55d5d885272840c7e42ba41ab1d5489f693419882f5`.
This changes no application or database data. New machines still need network
access to the chosen package and image registries.

## Scope limits

The initial cleanup removed `Experiment/` too broadly. It has been restored
from `cf1e6f75b973eb9e6425cb8ee9d039e40bd9cf9c`: all 3,631 tracked files under
`BPMNwithDMNcase/`, `NoiseExperiment/`, `PerformanceTest/` and `new/`.
The restored Git tree is identical to that baseline, preserving the original
release layout and recorded data. This restoration does not rerun experiments
or import development-only experiment directories.

Oracle/OCR, Fabric/Geth network provisioning, FireFly contract registration,
real DMN evaluation and cross-chain relaying require their external components
and selected environment configuration. They were retained and documented,
but this cleanup run did not redeploy blockchain networks or re-execute the
original paper workloads. A running web interface is not evidence of those
additional operations.

The small source smoke workflow under `.github/workflows/release-smoke.yml`
checks generator regressions and a clean frontend build. Its remote CI result
is not claimed here before GitHub executes it.

Temporary clean-install environments and exported source directories were removed after verification; logs, generated primary outputs and JSON results remain in the ignored .release-verification directory. No second Git checkout/worktree remains.
