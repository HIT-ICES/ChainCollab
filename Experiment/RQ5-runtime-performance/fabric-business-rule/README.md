# Fabric BusinessRuleTask timing

The [result archive](results-100/RESULTS.md) contains 100 valid runs from 100 attempts. See the [timing CSV](results-100/timings.csv), [mean timeline](results-100/fabric_businessrule_timeline_mean.pdf), and [independent verification](results-100/final-verification.json).

The [fixture](deployment/BusinessRuleTiming.bpmn) is Start → Score Decision → End. Each trial creates a fresh instance before timing. The reused DMN decision `Decision_timing` returns `approved=true` for the initial empty score. The generated chaincode emits `DMNContentRequired`. A WebSocket executor receives the corresponding event, downloads the DMN by CID, and invokes `Continue`. The continuation validates the content hash, calls the Fabric DMNEngine chaincode, and stores the result in `StateMemory.Approved`. Deployment, instance initialization, DMN publication, and CID binding are outside the measured interval.

| Stage | Interval |
| --- | --- |
| API Invoker | Rule request start to its FireFly operation creation |
| BPMN SC | First operation creation to its matching success event |
| Event Bus | That success event to the executor's receipt of `DMNContentRequired` |
| Executor | Executor receipt to the complete Continue response |
| IPFS | DMN download request to receipt of the complete response |
| API Invoker2 | Continue request start to the second operation creation |
| DMN SC | Second operation creation to its matching success event |

The Executor interval includes the IPFS download and part of the Continue path. DMN SC measures the Continue transaction with the DMNEngine call and confirmation. Each round records the event associations and clock samples used to align FireFly timestamps with the client clock.

From the repository root, prepare the fixture in a configured Fabric environment and write new measurements outside the archive:

```bash
src/backend/venv/bin/python Experiment/RQ5-runtime-performance/fabric-business-rule/prepare_fixture.py --stage all
src/backend/venv/bin/python Experiment/RQ5-runtime-performance/fabric-business-rule/run_repeat.py \
  --config Experiment/RQ5-runtime-performance/fabric-business-rule/config.live.json \
  --rounds 100 --max-attempts 120 --output .runtime/fabric-brt-timing
```

`prepare_fixture.py` records deployment state and generates the local configuration. Use `recalculate.py --input /path/to/copied/results.json` to replay the saved clock calculations offline and `draw.py --input /path/to/copied/results.json` with Matplotlib to regenerate the figure.
