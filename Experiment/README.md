# ChainCollab experimental artifact

This index follows Section V of the ChainCollab paper. The release uses the application and timing workloads from `dev-MultiBlockchain` at `afaa3e7717b891741fd5c5edae7e1e969e803cd2`, together with the existing release experiment layout. See the [installation guide](../Readme.md) for the system setup. Run the commands below from the repository root.

The [structured BPMN and companion DMN models](BPMNwithDMNcase/new/) include the eleven case studies and the SupplyChainPaper example. The [parent directory](BPMNwithDMNcase/) retains the earlier inputs referenced by the archived verification reports. Use the input attached to each recorded experiment when inspecting or replaying that run.

| Paper section | Experiment | Code and evidence |
| --- | --- | --- |
| V-B · RQ1A | Target-model legality | [Ecore and OCL checker](../src/newTranslator/MDAcheck/), [dataset manifest](new/exp1_mapping/target_model_validity/all_ocl_rules_try1/dataset_manifest.json), [coverage report](new/exp1_mapping/target_model_validity/all_ocl_rules_try1/coverage_completion_report.md). The archive includes 11 positive, 299 random negative, and 140 targeted negative XMI inputs. |
| V-B · RQ1B | Structural preservation | [Mapping contract](new/exp1_1B/contracts/default_mapping_contract.json), [checker](new/exp1_1B/scripts/), and [eleven-case batch report](new/exp1_1B/cases/batch_summary.md). Per-case reports are in `cases/<case>/reports/`. |
| V-B · RQ1C | Bounded behavioral preservation | [UBTS scripts](new/exp1_1C/scripts/) and [case evidence](new/exp1_1C/cases/). Each case includes its logical paths and comparison results. The 75 logical paths feed RQ3. |
| V-C · RQ2 | Static semantic fidelity | [AST-based checker](new/exp2_semantic_verification/scripts/), [eleven DSL inputs](../src/newTranslator/MDAcheck/bpmn-positive/b2c/), and [archived results](new/exp2_semantic_verification/results/). The archived tooling uses its historical SV identifiers. Consult the paper for the assertion numbering used in Section V. |
| V-D · RQ3 | Cross-platform runtime traces | [Replay and comparison scripts](new/exp3/scripts/) and [normalized traces and comparison reports](new/exp3/outputs/). There are 75 reports for each of DSL–Fabric, DSL–Geth, and Fabric–Geth, covering 1,100 aligned steps per platform and zero reported mismatches. |
| V-E · RQ4 | Execution correctness | [Path perturbation and Fabric replay](NoiseExperiment/) and [archived inputs and outcomes](NoiseExperiment/done/). See the evidence coverage note below. |
| V-F · RQ5 | Runtime performance | [Four timing workloads and recorded results](#rq5-runtime-performance). |

## RQ1–RQ3 verification

After installing ChainCollab, validate the archived RQ1A XMI corpus with Java 17 and Maven. The runner obtains Eclipse OCL and EMF dependencies from the p2 repository configured in its POM.

```bash
checker="$PWD/src/newTranslator/MDAcheck"
dataset="$PWD/Experiment/new/exp1_mapping/target_model_validity/all_ocl_rules_try1"
bash "$checker/run_ocl_validate_batch.sh" "$dataset" "$checker/b2c.ecore" \
  "$checker/check.ocl" "$PWD/.runtime/paper-experiments/rq1a"
```

To regenerate the RQ1B structural checks for the archived inputs:

```bash
src/newTranslator/.venv/bin/python Experiment/new/exp1_1B/scripts/run_all_bpmn_cases.py \
  --bpmn-dir Experiment/BPMNwithDMNcase \
  --out-dir .runtime/paper-experiments/rq1b
```

For RQ1C, the [UBTS pipeline](new/exp1_1C/scripts/) defaults to SupplyChainPaper and the bound `K = (30, 2, 200)`. Use a separate output root for new runs:

```bash
EXP1C_OUTPUT_ROOT=.runtime/paper-experiments/rq1c \
  src/newTranslator/.venv/bin/python \
  Experiment/new/exp1_1C/scripts/run_supplychainpaper_pipeline.py
```

For other cases, set `EXP1C_CASE_NAME` and `EXP1C_BPMN_FILE` to the case ID and the absolute path of its archived source model. For RQ2, install the [checker dependencies](new/exp2_semantic_verification/requirements.txt) and make Go, Node.js, and the Solidity compiler available:

```bash
src/newTranslator/.venv/bin/python Experiment/new/exp2_semantic_verification/scripts/run_exp2.py \
  --results-dir .runtime/paper-experiments/rq2
```

The RQ2 checker recognizes the current Solidity `Complete` function as the handler for a completed message. The historical outputs and assertion IDs remain available for audit.

To compare an existing RQ3 trace pair offline:

```bash
trace_dir=Experiment/new/exp3/outputs/SupplyChainPaper/paths/SupplyChainPaper_auto_path_001/normalized
python3 Experiment/new/exp3/scripts/compare_normalized_traces.py \
  --left "$trace_dir/dsl.normalized.json" \
  --right "$trace_dir/solidity.normalized.json"
```

Each path has three normalized traces and three pairwise comparison reports. `comparison.json` compares DSL–Geth, `comparison.dsl_fabric.json` compares DSL–Fabric, and `comparison.solidity_fabric.json` compares Geth–Fabric. Live replay requires the corresponding network, deployed contracts, FireFly API, participant bindings, and rule services. Configure the current deployment using the [replay guide](new/exp3/README.md). Absolute paths and deployment identifiers inside saved reports refer to the original runs.

## RQ4 evidence coverage

The released Fabric archive contains 50 base-path result files across 11 cases, with 6,917 raw outcome records. Section V reports a final workload of 111 conforming and 6,809 non-conforming paths on each platform. The available Fabric archive is short of that final workload, and the matching Geth perturbation replay archive could not be located. RQ3 traces cover the separate verified-path experiment. The [NoiseExperiment guide](NoiseExperiment/readme.md) describes the available perturbation and Fabric replay procedure.

## RQ5 runtime performance

Each workload includes 100 retained runs, its collection and plotting scripts, per-run JSON, a timing CSV, and a stage summary. The file-message workload measures `Message_Send` with a fresh 1 KiB file. The rule workload starts a fresh process instance with a reused 899-byte DMN model. Geth rule measurements use Chainlink DirectRequest and CDMN. The stage intervals can overlap.

| Workload | Protocol and entry point | Archived results |
| --- | --- | --- |
| Fabric file message | [Guide](PerformanceTest/FabricMessageTiming/README.md) and [collector](PerformanceTest/FabricMessageTiming/run_repeat.py) | [Report](PerformanceTest/FabricMessageTiming/results-100/RESULTS.md), [timings](PerformanceTest/FabricMessageTiming/results-100/timings.csv), [figure](PerformanceTest/FabricMessageTiming/results-100/fabric_message_timeline_mean.pdf) |
| Geth file message | [Guide](PerformanceTest/GethMessageTiming/README.md) and [collector](PerformanceTest/GethMessageTiming/run_repeat.py) | [Report](PerformanceTest/GethMessageTiming/results-100/RESULTS.md), [timings](PerformanceTest/GethMessageTiming/results-100/timings.csv), [figure](PerformanceTest/GethMessageTiming/results-100/geth_message_timeline_mean.pdf) |
| Fabric BusinessRuleTask | [Guide](PerformanceTest/FabricBusinessRuleTiming/README.md) and [collector](PerformanceTest/FabricBusinessRuleTiming/run_repeat.py) | [Report](PerformanceTest/FabricBusinessRuleTiming/results-100/RESULTS.md), [timings](PerformanceTest/FabricBusinessRuleTiming/results-100/timings.csv), [figure](PerformanceTest/FabricBusinessRuleTiming/results-100/fabric_businessrule_timeline_mean.pdf) |
| Geth BusinessRuleTask | [Guide](PerformanceTest/GethBusinessRuleTiming/README.md) and [collector](PerformanceTest/GethBusinessRuleTiming/run_batch.py) | [Report](PerformanceTest/GethBusinessRuleTiming/results-100/RESULTS.md), [timings](PerformanceTest/GethBusinessRuleTiming/results-100/timings.csv), [figure](PerformanceTest/GethBusinessRuleTiming/results-100/geth_businessrule_timeline_mean.pdf) |

For offline inspection, read each `results-100/summary.json` and `round-N/result.json`. Run the workload's `draw.py` against a copy of the result directory to regenerate its figure. Plotting requires Matplotlib. For live measurements, follow the workload guide and create a local `config.live.json` where required using the current deployment and the [Oracle and Relayer setup guide](../docs/ORACLE_RELAYER_SETUP.md). Deployment records describe the original measurement environment. Use a new output directory for new runs.

To check the archived Geth BusinessRuleTask sample hashes, execution evidence, and stage calculations offline:

```bash
src/backend/venv/bin/python Experiment/PerformanceTest/GethBusinessRuleTiming/verify_results.py
```

The [PlatformTPSComparison archive](PerformanceTest/PlatformTPSComparison/) contains supplementary throughput runs. Section V's stage latency figures use the four timing workloads above.
