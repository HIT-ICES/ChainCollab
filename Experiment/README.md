# ChainCollab experimental artifact

This index follows Section V of the ChainCollab paper. The release uses the application and timing workloads from `dev-MultiBlockchain` at `afaa3e7717b891741fd5c5edae7e1e969e803cd2`, together with the archived verification results. See the [installation guide](../Readme.md) for the system setup. Run the commands below from the repository root.

The [structured BPMN and companion DMN models](BPMNwithDMNcase/) are the canonical example set. The eleven [historical BPMN fixtures](fixtures/) preserve the source models used in the archived RQ1B and RQ1C runs. Both sets use the same DMN files. Older paths in archived reports identify the source of the recorded run.

| Paper section | Experiment | Code and evidence |
| --- | --- | --- |
| V-B · RQ1A | [Target-model legality](RQ1A-target-model-legality/) | [Ecore and OCL checker](../src/newTranslator/MDAcheck/), [dataset manifest](RQ1A-target-model-legality/dataset/dataset_manifest.json), and [coverage report](RQ1A-target-model-legality/dataset/coverage_completion_report.md). The archive includes 11 positive, 299 random negative, and 140 targeted negative XMI inputs. |
| V-B · RQ1B | [Structural preservation](RQ1B-structural-preservation/) | [Mapping contract](RQ1B-structural-preservation/contracts/default_mapping_contract.json), [checker](RQ1B-structural-preservation/scripts/), and [eleven-case batch report](RQ1B-structural-preservation/cases/batch_summary.md). |
| V-B · RQ1C | [Bounded behavioral preservation](RQ1C-bounded-behavioral-preservation/) | [UBTS scripts](RQ1C-bounded-behavioral-preservation/scripts/) and [case evidence](RQ1C-bounded-behavioral-preservation/cases/). The 75 logical paths feed RQ3. |
| V-C · RQ2 | [Static semantic fidelity](RQ2-static-semantic-fidelity/) | [AST-based checker](RQ2-static-semantic-fidelity/scripts/), [eleven DSL inputs](../src/newTranslator/MDAcheck/bpmn-positive/b2c/), and [archived results](RQ2-static-semantic-fidelity/results/). Consult the paper for the assertion numbering used in Section V. |
| V-D · RQ3 | [Runtime trace consistency](RQ3-runtime-trace-consistency/) | [Replay scripts](RQ3-runtime-trace-consistency/scripts/) and [normalized comparisons](RQ3-runtime-trace-consistency/outputs/). Each platform pair has 75 comparisons covering 1,100 aligned steps. |
| V-E · RQ4 | [Generated-code execution correctness](RQ4-execution-correctness/) | [Archived inputs and Fabric outcomes](RQ4-execution-correctness/done/). See the evidence coverage note below. |
| V-F · RQ5 | [Runtime performance](RQ5-runtime-performance/) | [Four timing workloads and recorded results](#rq5-runtime-performance). |

## RQ1–RQ3 verification

After installing ChainCollab, validate the archived RQ1A XMI corpus with Java 17 and Maven. The runner obtains Eclipse OCL and EMF dependencies from the p2 repository configured in its POM.

```bash
checker="$PWD/src/newTranslator/MDAcheck"
dataset="$PWD/Experiment/RQ1A-target-model-legality/dataset"
bash "$checker/run_ocl_validate_batch.sh" "$dataset" "$checker/b2c.ecore" \
  "$checker/check.ocl" "$PWD/.runtime/paper-experiments/rq1a"
```

To regenerate the RQ1B structural checks for the archived inputs:

```bash
src/newTranslator/.venv/bin/python Experiment/RQ1B-structural-preservation/scripts/run_all_bpmn_cases.py \
  --bpmn-dir Experiment/fixtures \
  --out-dir .runtime/paper-experiments/rq1b
```

For RQ1C, the [UBTS pipeline](RQ1C-bounded-behavioral-preservation/scripts/) defaults to SupplyChainPaper and the bound `K = (30, 2, 200)`. Use a separate output root for new runs:

```bash
EXP1C_OUTPUT_ROOT=.runtime/paper-experiments/rq1c \
  src/newTranslator/.venv/bin/python \
  Experiment/RQ1C-bounded-behavioral-preservation/scripts/run_supplychainpaper_pipeline.py
```

For other cases, set `EXP1C_CASE_NAME` and `EXP1C_BPMN_FILE` to the case ID and the absolute path of its archived source model. For RQ2, install the [checker dependencies](RQ2-static-semantic-fidelity/requirements.txt) and make Go, Node.js, and the Solidity compiler available:

```bash
src/newTranslator/.venv/bin/python Experiment/RQ2-static-semantic-fidelity/scripts/run_exp2.py \
  --results-dir .runtime/paper-experiments/rq2
```

The RQ2 checker recognizes the current Solidity `Complete` function as the handler for a completed message. The historical outputs and assertion IDs remain available for audit.

To compare an existing RQ3 trace pair offline:

```bash
trace_dir=Experiment/RQ3-runtime-trace-consistency/outputs/SupplyChainPaper/paths/SupplyChainPaper_auto_path_001/normalized
python3 Experiment/RQ3-runtime-trace-consistency/scripts/compare_normalized_traces.py \
  --left "$trace_dir/dsl.normalized.json" \
  --right "$trace_dir/solidity.normalized.json"
```

Each path has three normalized traces and three pairwise comparison reports. `comparison.json` compares DSL–Geth, `comparison.dsl_fabric.json` compares DSL–Fabric, and `comparison.solidity_fabric.json` compares Geth–Fabric. Live replay requires the corresponding network, deployed contracts, FireFly API, participant bindings, and rule services. Configure the current deployment using the [replay guide](RQ3-runtime-trace-consistency/README.md). Absolute paths and deployment identifiers inside saved reports refer to the original runs.

## RQ4 evidence coverage

The released Fabric archive contains 50 base-path result files across 11 cases, with 6,917 raw outcome records. Section V reports a final workload of 111 conforming and 6,809 non-conforming paths on each platform. The available Fabric archive is short of that final workload, and the matching Geth perturbation replay archive could not be located. The [RQ4 guide](RQ4-execution-correctness/README.md) describes the available perturbation and Fabric replay procedure.

## RQ5 runtime performance

Each workload includes 100 retained runs, its collection and plotting scripts, per-run JSON, a timing CSV, and a stage summary. The file-message workload measures `Message_Send` with a fresh 1 KiB file. The rule workload starts a fresh process instance with a reused 899-byte DMN model. Geth rule measurements use Chainlink DirectRequest and CDMN. The stage intervals can overlap.

| Workload | Protocol and entry point | Archived results |
| --- | --- | --- |
| Fabric file message | [Guide](RQ5-runtime-performance/fabric-file-message/README.md) and [collector](RQ5-runtime-performance/fabric-file-message/run_repeat.py) | [Report](RQ5-runtime-performance/fabric-file-message/results-100/RESULTS.md), [timings](RQ5-runtime-performance/fabric-file-message/results-100/timings.csv), [figure](RQ5-runtime-performance/fabric-file-message/results-100/fabric_message_timeline_mean.pdf) |
| Geth file message | [Guide](RQ5-runtime-performance/geth-file-message/README.md) and [collector](RQ5-runtime-performance/geth-file-message/run_repeat.py) | [Report](RQ5-runtime-performance/geth-file-message/results-100/RESULTS.md), [timings](RQ5-runtime-performance/geth-file-message/results-100/timings.csv), [figure](RQ5-runtime-performance/geth-file-message/results-100/geth_message_timeline_mean.pdf) |
| Fabric BusinessRuleTask | [Guide](RQ5-runtime-performance/fabric-business-rule/README.md) and [collector](RQ5-runtime-performance/fabric-business-rule/run_repeat.py) | [Report](RQ5-runtime-performance/fabric-business-rule/results-100/RESULTS.md), [timings](RQ5-runtime-performance/fabric-business-rule/results-100/timings.csv), [figure](RQ5-runtime-performance/fabric-business-rule/results-100/fabric_businessrule_timeline_mean.pdf) |
| Geth BusinessRuleTask | [Guide](RQ5-runtime-performance/geth-business-rule/README.md) and [collector](RQ5-runtime-performance/geth-business-rule/run_batch.py) | [Report](RQ5-runtime-performance/geth-business-rule/results-100/RESULTS.md), [timings](RQ5-runtime-performance/geth-business-rule/results-100/timings.csv), [figure](RQ5-runtime-performance/geth-business-rule/results-100/geth_businessrule_timeline_mean.pdf) |

For offline inspection, read each `results-100/summary.json` and `round-N/result.json`. Run the workload's `draw.py` against a copy of the result directory to regenerate its figure. Plotting requires Matplotlib. For live measurements, follow the workload guide and create a local `config.live.json` where required using the current deployment and the [Oracle and Relayer setup guide](../docs/ORACLE_RELAYER_SETUP.md). Deployment records describe the original measurement environment. Use a new output directory for new runs.

To check the archived Geth BusinessRuleTask sample hashes, execution evidence, and stage calculations offline:

```bash
src/backend/venv/bin/python Experiment/RQ5-runtime-performance/geth-business-rule/verify_results.py
```

The [supplementary directory](supplementary/) contains throughput runs, the static fidelity development suite, and earlier design notes. Section V's stage latency figures use the four timing workloads above.
