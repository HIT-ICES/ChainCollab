# RQ2: Static semantics of generated Go and Solidity

This suite extracts a semantic representation from B2CDSL and analyzes ASTs from the generated Go chaincode and Solidity contracts. It checks storage, participants, messages, gateways, events, business rules, oracle tasks, and flow effects. The [assertion table](ASSERTION_TABLE.md) and [mapping rules](MAPPING_RULES.md) describe the checker. Archived assertion identifiers follow the historical checker numbering.

[Case manifests](cases/) identify the input B2CDSL or BPMN for each case. Generated code and evidence are in [results/cases](results/cases/), with [the batch summary](results/exp2_summary.md) and [assertion coverage](results/assertion_coverage.md) as entry points.

## Run the batch

Complete the [repository setup](../../Readme.md), install the [checker requirements](requirements.txt) in the translator environment, and ensure Go, Node.js, and `solc` are on your PATH. From the repository root:

```bash
src/newTranslator/.venv/bin/python Experiment/RQ2-static-semantic-fidelity/scripts/run_exp2.py \
  --results-dir .runtime/paper-experiments/rq2
```

The default CLI backend invokes the local generator. To use the translator service, select `--backend api` and provide `--api-base-url`. Use `--cases-dir` or `--assertion-table` to select alternative inputs. Inspect `run_log.json` for errors and the per-case verification reports for matching evidence. The [runtime trace suite](../RQ3-runtime-trace-consistency/README.md) covers execution behavior.
