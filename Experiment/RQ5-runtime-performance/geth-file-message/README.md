# Geth file-message timing

The [100-run report](results-100/RESULTS.md) describes 134 attempts, of which 21 exceeded the 25-second transaction threshold and 13 had invalid timing. The reported values describe the retained 100 rounds. See the [timing CSV](results-100/timings.csv), [mean timeline](results-100/geth_message_timeline_mean.pdf), and [verification record](results-100/verification.json).

## Run against a deployed fixture

The workload repeats `Message_1wswgqu` on an existing instance with an enabled, repeatable file message. Each round uploads a new 1 KiB file. The collector calls the same authenticated `prepare-file-message` endpoint as the Geth execution page, invokes the contract with the returned FireFly message ID, and verifies file bytes on the receiver side and through IPFS. The receiver-side Complete call is outside the workload.

Run from the repository root and substitute the BPMN, instance, message, and signer for your deployment:

```bash
src/backend/venv/bin/python Experiment/RQ5-runtime-performance/geth-file-message/run_repeat.py \
  --bpmn <bpmn-uuid> --instance <instance-uuid> --message Message_1wswgqu \
  --signer <ethereum-address> --rounds 3 --output .runtime/geth-message-smoke
```

The [batch driver](run_batches.py) reproduces the archived protocol on its configured target. It runs a batch, excludes rounds whose transaction interval is strictly greater than 25 seconds, then measures replacements for the excluded rounds. Supply a new output directory. For an alternative target, use `run_repeat.py --help` for endpoint, signer, threshold, and resume options. Its per-attempt threshold mode differs from the archived batch protocol.

## Timing and evidence

The private data interval runs from the upload request through private delivery and publication confirmation. The IPFS interval measures file publication. The API and blockchain intervals meet at the matching FireFly operation's creation timestamp. See [timing definitions](TIMING_DEFINITIONS.md) for event fields and clock normalization.

The results directory contains per-round JSON, `results.json`, `summary.json`, and `timings.csv`. Use `summarize.py` to recompute statistics offline and `draw.py --input /path/to/copied/results.json --output-dir /path/to/plots` with Matplotlib to regenerate the timeline.
