# Issues and limits

## Runtime errors

1. **Go compile: FAIL.** `fabric/raw/go.mod` requires Go 1.23.1, while the installed `/usr/local/go/bin/go` is 1.22.0. The first check with `GOTOOLCHAIN=local` rejected the version (`logs/B_go_compile.stderr`). A second check with `GOTOOLCHAIN=auto` attempted to download Go 1.23.1 but timed out at `proxy.golang.org` (`logs/B_go_compile_auto.stderr`). This is an environment/toolchain failure; it is not evidence that the generated Go code compiles or fails at the source level.

## Static observations

1. **The supplied DMN was not read by BPMN→DSL.** `generation_contexts/A_file_reads.json` records the Python audit events for the sidecar rerun. It includes `SupplyChainPaper.bpmn` and `generator/bindings.json`, but not `supplyChainPaper.dmn`. The Go and Solidity generation read audits likewise consume the generated B2CDSL and generator assets, not the supplied DMN.
2. **The emitted binding does not match the DMN IDs.** Raw B2CDSL lines 178–179 contain `Activity_0rm8bkp.dmn` and `Activity_0rm8bkp_DecisionID`, synthesized in `generator/translator.py`. The supplied file is `supplyChainPaper.dmn`, whose decisions are `decision_0tybghz` and `Decision_0zwjfyy`. No correction was applied.
3. **The two-decision dependency is declared, not executed here.** The DMN XML contains `Decision_0zwjfyy` → `requiredDecision href="#decision_0tybghz"`. Generated platform code accepts runtime DMN content/CID and a decision ID. No engine/network was run, so dependency support and the correct decision-selection behavior remain unverified.
4. **Bindings partly come from BPMN and partly from defaults/runtime parameters.** Input/output mappings come from the BPMN business-rule documentation. Participant MSP/attributes come from `generator/bindings.json` when present, otherwise name-derived defaults. Go receives DMN content, decision ID, and ParamMapping in init parameters; Solidity receives CID, decision ID, caller, and evaluation endpoint through initialization structures.
5. **The diagnostic context is not a native PSM.** `generation_contexts/*.context*.json` and `geth.execution_layout.diagnostic.json` are sidecar dumps made by wrapping the original renderers. The native/sidecar outputs are byte-identical according to `generation_contexts/native_sidecar_comparison.json`.
6. **Case constructs.** The model contains a parallel split (`Gateway_0onpe6x`) and join (`Gateway_1fbifca`) with predecessor set `Message_0cba4t6`, `Message_0pm90nx`. It contains no event-based gateway, Oracle receive/script task, or dual-message choreography task; no such constructs were fabricated.

## Unverified risks and absent artifacts

1. Chain deployment and transaction execution were intentionally NOT_RUN. External Fabric Oracle/DMNEngine behavior, Geth `IDmnLite` behavior, participant accounts/organizations, CID/content, initialization values, and the actual DMN response shape were not validated.
2. The generator did not emit a native FFI. Solidity ABI and bytecode in `geth/compiled/` were produced by the compile check, and execution layout exists only as a diagnostic dump. No absent FFI was synthesized.
3. Solidity compiled successfully with installed solc-js 0.8.33. That proves compiler acceptance only, not deployment or runtime correctness.
4. `existing_artifacts/` contains historical candidates confirmed by both distinctive BPMN IDs or both DMN decision IDs. This correspondence identifies the case family; it does not certify byte equivalence to the current source models.
