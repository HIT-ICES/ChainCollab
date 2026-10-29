# SupplyChainPaper reproduction archive

This archive records an unmodified run of the local ChainCollab conversion chain at branch `release-MultiBlockchain`, commit `8321eef08c96e78f2bac67eec19bb4d566418841`. It separates new raw products from historical references and diagnostic sidecars.

| Stage | Status | Evidence |
|---|---|---|
| Input files checked | PASS | evidence/input_checksums.csv; archived files byte-equal |
| BPMN → B2CDSL | PASS | logs/A_bpmn_to_dsl.json; pim/SupplyChainPaper.b2c |
| B2CDSL grammar parse | PASS | logs/A_parse.json |
| B2CDSL → Fabric/Go | PASS | logs/B_go_generate.json; fabric/raw/ |
| B2CDSL → Geth/Solidity | PASS | logs/C_solidity_generate.json; geth/raw/SupplyChainPaper.sol |
| Generation-context export | PASS | logs/D_diagnostic.json; generation_contexts/native_sidecar_comparison.json |
| Go compile | FAIL | logs/B_go_compile.json and logs/B_go_compile_auto.json |
| Solidity compile | PASS | logs/C_solidity_compile.json; geth/compiled/ |
| Chain deployment/execution | NOT_RUN | out of scope; no deployment or transactions |

## Main products

- `source_models/`: byte-preserved BPMN and DMN, with origin and hashes in `evidence/input_checksums.csv`.
- `pim/SupplyChainPaper.b2c`: raw converter output. `evidence/platform_pim_hashes.json` records the identical PIM SHA-256 used for both platforms.
- `fabric/raw/`: all Go generator outputs and copied scaffold dependencies.
- `geth/raw/SupplyChainPaper.sol`: raw Solidity generator output.
- `geth/compiled/`: ABI and bytecode emitted by the successful solc-js compile check.
- `generation_contexts/`: actual renderer context dumps, template-call dumps, execution-layout diagnostic, read audits, and byte-identity comparisons.
- `generator_snapshot/`: minimal converter/parser/grammar/snippet/renderer/template/configuration snapshot with original relative paths.
- `existing_artifacts/`: historical case-family references only.
- `evidence/traceability.csv`, `evidence/worked_mapping_extracts.md`, and `evidence/issues.md`: case-specific mapping and limitations.

## DMN finding

The BPMN converter did not read `supplyChainPaper.dmn`. It generated the placeholder binding `Activity_0rm8bkp.dmn` / `Activity_0rm8bkp_DecisionID` from the BPMN task ID, while the supplied DMN decisions are `decision_0tybghz` and `Decision_0zwjfyy`. The XML dependency exists in the source, but no DMN engine execution was performed. The raw mismatch is preserved in every product.

## Integrity and workspace state

Protected input and generator snapshot source hashes are unchanged: **true** (`evidence/protected_hash_verification.json`). No source model, generator, grammar, renderer, or template was edited. `logs/git_preexisting_filtered.stdout` records unrelated pre-existing untracked files with this archive excluded. The archive itself is an untracked output under `artifacts/`.

`manifest.csv` lists archive-relative paths, origins/commands, stages, file nature, and SHA-256. It excludes itself because a stable self-hash is impossible. `reproduce.sh` refuses to overwrite an existing target and reruns into a new directory.
