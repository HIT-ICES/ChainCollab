# RQ1B extension: traceability of RQ3 paths

This supplementary checker follows RQ3 logical operations back through the RQ1B source-to-DSL trace. It reads each case's `bpmn_dsl_trace.json` and RQ3 logical paths, checks whether their triggers and operations are traceable, and writes per-case reports plus a batch summary. See the [archived batch summary](cases/addition_batch_summary.md).

Run from the repository root:

```bash
python3 Experiment/RQ1B-structural-preservation/rq3-path-traceability/scripts/run_all_addition_cases.py \
  --out-dir .runtime/paper-experiments/rq1b-traceability
```

Use `--exp3-cases-dir` and `--exp1b-cases-dir` to point to different inputs. The defaults use the archived cases in this release.
