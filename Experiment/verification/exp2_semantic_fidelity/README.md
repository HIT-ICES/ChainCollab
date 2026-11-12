# Static semantic fidelity development suite

This earlier suite exercises the B2CDSL-to-Go/Solidity generation and comparison pipeline with focused cases. For the paper's eleven-case RQ2 batch, use the [semantic verification suite](../exp2_semantic_verification/README.md).

The runner invokes the project's generators, extracts a B2CDSL intermediate representation and Go/Solidity syntax evidence, then checks element structure and flow effects. It writes generated code, normalized representations, and per-case reports. The [assertion table](ASSERTION_TABLE.md) records the checks used by this suite. Its outputs concern static evidence. Live replay is documented in [RQ3](../exp3/README.md).

Install the [Python dependencies](requirements.txt), set up the translator, and make Go, Node.js, and the Solidity compiler available. From this directory:

```bash
python3 run_exp2.py --input cases/positive/basic_linear_case.b2c \
  --outdir /path/to/new-output/basic_linear_case
```

The runner also accepts BPMN inputs. Use `--help` for input, output, and batch options. The [outputs](outputs/) directory preserves the recorded experiments.
