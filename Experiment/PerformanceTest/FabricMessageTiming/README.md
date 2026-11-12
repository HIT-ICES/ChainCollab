# Fabric file-message timing

This workload measures the generated Fabric message submission path with a fresh 1 KiB attachment. The 100 retained runs came from 108 attempts. Eight attempts had invalid clock mappings and none exceeded the 25-second transaction threshold. See the [result report](results-100/RESULTS.md), [timing CSV](results-100/timings.csv), [mean timeline](results-100/fabric_message_timeline_mean.pdf), and [verification record](results-100/final-verification.json).

## Fixture and state checks

[FabricFileTiming.bpmn](deployment/FabricFileTiming.bpmn) declares the required `orderDetails` attachment and the scalar `requestId=1` on `Message_1wswgqu`. The scalar keeps the Fabric chaincode's state-memory structure nonempty. [generated.go](deployment/generated.go) preserves the generator output. The installed [experimental copy](deployment/smartcontract.go) uses the [repeatable-message patch](deployment/repeatable-message.patch) to leave the target message enabled across trials. It still checks the sender, persists the FireFly message ID, and emits the event. The collector compares message, event, gateway, and rule snapshots and checks that only the target message's FireFly ID changes. These trials measure Send. The receiver-side Complete operation is outside the workload.

## Configure and run

Use an existing Fabric network and FireFly cores in distinct organizations. Copy [config.example.json](config.example.json) and supply the sender and recipient namespace URLs, the registered chaincode API, the IPFS gateway, the repeatable instance and message IDs, the recipient DID, and the sender signing identity. Specify the attachment name in `file_field` and scalar inputs in `values` and `contract_input`. Optional `parameters` overrides resolve ambiguous ABI parameter names. Use `header_env` to reference local authentication variables.

From the repository root, use the backend Python environment with `requests` installed:

```bash
src/backend/venv/bin/python Experiment/PerformanceTest/FabricMessageTiming/run_repeat.py \
  --config /path/to/fabric-timing.json --check-config

src/backend/venv/bin/python Experiment/PerformanceTest/FabricMessageTiming/run_repeat.py \
  --config /path/to/fabric-timing.json --rounds 100 --max-red-seconds 25 \
  --output .runtime/fabric-message-timing
```

For a new fixture, run `generate_fixture.py --owner-bpmn <source-bpmn-uuid>` and `deploy_fixture.py --stage all` from the same directory using the backend environment. They require a configured deployment and write its metadata and `config.live.json`. The collector accepts an existing deployment without running those scripts.

## Stage boundaries

| Stage | Interval |
| --- | --- |
| Private Data Bus | Upload request to confirmed private delivery and publication completion |
| IPFS | Publication request to confirmed publication and CID |
| API Invoker | Contract request start to the matching FireFly operation's creation |
| BPMN SC | That operation's creation to its matching blockchain success event |

The API and chain intervals share the same operation timestamp. The IPFS interval is part of the broader private data interval. Client monotonic and server timestamps are aligned using the saved clock samples. The collector verifies the file bytes and rejects invalid clock mappings. A transaction duration strictly above 25 seconds excludes the round. A duration of exactly 25 seconds is retained.

Run `draw.py --input /path/to/copied/results.json --output-dir /path/to/plots` with Matplotlib to reproduce the mean timeline from a copy of the archive.
