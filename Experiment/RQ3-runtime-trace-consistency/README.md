# RQ3: Cross-platform runtime trace consistency

The suite replays the same bounded logical paths through the B2CDSL simulator, Fabric, and Geth. Each execution line produces a trace. After normalization, the checker compares triggers, enabled sets, step acceptance, state and variable changes, decision write-back, and final state.

| Directory | Contents |
| --- | --- |
| [cases](cases/) | Shared paths in `<case>/paths/<path>/logical_path.json` |
| [dsl](dsl/README.md) | Simulator inputs and reference traces |
| [fabric](fabric/README.md) | Fabric replay inputs and recorded results |
| [solidity](solidity/README.md) | Geth replay inputs and recorded results |
| [outputs](outputs/) | Normalized traces and the three pairwise comparisons |
| [scripts](scripts/) | Path materialization, execution, normalization, and comparison |

Each `outputs/<case>/paths/<path>/` directory contains `comparison.json` for DSL–Geth, `comparison.dsl_fabric.json` for DSL–Fabric, and `comparison.solidity_fabric.json` for Geth–Fabric. See the [experiment index](../README.md) for an offline comparison command.

## Replay a path

Start from a verified logical path and use [materialize_logical_path.py](scripts/materialize_logical_path.py) to prepare simulator and Solidity inputs. Fabric consumes the logical path directly. Configure the contract API, participant bindings, signing identities, and rule services for the target deployment before running the live scripts. Inspect each script's `--help` for configuration and output paths.

- [run_exp3.py](scripts/run_exp3.py) executes the DSL simulator.
- [run_case_pipeline.py](scripts/run_case_pipeline.py) enumerates paths, runs the simulator and Solidity replay, and compares normalized traces.
- [run_fabric_case_paths.py](scripts/run_fabric_case_paths.py) replays a case's logical paths on Fabric and builds the Fabric comparisons.
- [normalize_traces.py](scripts/normalize_traces.py) and [compare_normalized_traces.py](scripts/compare_normalized_traces.py) can operate on recorded inputs.

The evidence covers the selected bounded paths and the normalization rules used in this release.
