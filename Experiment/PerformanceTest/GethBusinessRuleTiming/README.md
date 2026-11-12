# Geth BusinessRuleTask timing

The [100-run archive](results-100/RESULTS.md) records the DirectRequest and CDMN path. Of 145 attempts, 17 had invalid clock mappings and 28 exceeded one of the registered thresholds. The thresholds are 25 seconds for result write-back and 60 seconds from the initial request to Chainlink job start. Values equal to a threshold are retained. The reported means describe the retained runs. See the [timing CSV](results-100/timings.csv), [mean timeline](results-100/geth_businessrule_timeline_mean.pdf), and [run metadata](results-100/run-metadata.json).

A new process instance invokes the generated rule handler against the reused 899-byte [DMN](deployment/rule.dmn). The registered request triggers Chainlink DirectRequest and the CDMN worker. The worker retrieves the rule from IPFS and computes the result. The result is submitted on-chain, then the generated Continue function applies it and advances the workflow. The collector checks the request state, FireFly events, contract state, and the `approved` write-back. Deployment and initialization take place before timing.

| Stage | Interval |
| --- | --- |
| API Invoker | Initial request start to first FireFly operation creation |
| BPMN SC | First operation creation to its matching success event |
| Request to Chainlink job | Initial request start to the matching job's creation |
| Chainlink Executor | CDMN HTTP call start to the completed response |
| IPFS download | Rule retrieval request to the complete response observed in the CDMN network |
| Result commit on chain | Completed CDMN response to FireFly receipt of the matching result event |
| API Invoker2 | Continue request start to second FireFly operation creation |
| BPMN Continue SC | Second operation creation to the matching success event |

The request-to-job interval can overlap the initial API and blockchain intervals. The IPFS interval is nested within executor activity. Raw clock mappings, per-round records, and the sample SHA-256 manifest are retained.

## Reproduce or inspect

From the repository root, prepare a configured Geth environment with the corresponding Chainlink jobs, CDMN services, and sufficient development LINK, then run:

```bash
src/backend/venv/bin/python Experiment/PerformanceTest/GethBusinessRuleTiming/prepare_fixture.py
src/backend/venv/bin/python Experiment/PerformanceTest/GethBusinessRuleTiming/run_batch.py \
  --rounds 100 --output .runtime/geth-brt-timing
```

The fixture script records deployment details and creates `config.live.json`. Use the actual environment configuration and local Chainlink credentials. `--resume` continues a saved batch in the same output directory after the original process has stopped.

For offline verification:

```bash
src/backend/venv/bin/python Experiment/PerformanceTest/GethBusinessRuleTiming/verify_results.py
```

The verifier checks 100 sample hashes and recomputes 800 stage intervals. Run `draw.py --input /path/to/copied/results.json` with Matplotlib to generate a figure from a copy of the results directory.
