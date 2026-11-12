# Path perturbation and Fabric replay

This directory contains the RQ4 path generator, Fabric replay harness, and the available archive. See the [experiment index](../README.md) for evidence coverage.

- `path_raw/` holds source-derived base paths.
- `done/<case>/basic_path/` contains runnable path definitions. Each defines `steps`, an `invoke_path`, and optional `appended_index_paths`.
- `done/<case>/result/` contains recorded outcomes and detailed logs.
- `noise_generator.py` creates insertion, deletion, and swap variants. `invoker.py` creates an instance, runs the steps, and checks preconditions, postconditions, and BusinessRule continuation events.

## Run a replay

Use Python 3.12 and install [requirements.txt](requirements.txt) in a virtual environment. Configure the deployed Fabric API URL, participant signing identities, and instance creation arguments in `main.py` using the target process's runtime bindings. Run from this directory with a new output file:

```bash
python main.py run -input done/purchase/basic_path/path1.json \
  -output /path/to/new-result.json -N 100 -listen
```

`-N` selects the percentage of generated variants to replay. `-m ars` enables insertions, removals, and swaps. `-e` replays the base path and explicitly appended variants. Use `-listen` when a listener must be registered. The `FulfillTheRest/` scripts extract previously unresolved variants and merge separately collected follow-up results. Use copies when applying those scripts to a saved run.
