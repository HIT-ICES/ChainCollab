#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
REPO = Path("/home/shenxz-lab/code/ChainCollab")
EVIDENCE = OUT / "evidence"
LOGS = OUT / "logs"
EVIDENCE.mkdir(exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def first_line(path: Path, needle: str) -> int | None:
    for number, line in enumerate(lines(path), 1):
        if needle in line:
            return number
    return None


def ref(path: Path, needle: str, function: str = "") -> str:
    number = first_line(path, needle)
    suffix = f"; {function}" if function else ""
    return f"{path.relative_to(OUT)}:{number}{suffix}" if number else "NOT_FOUND"


def excerpt(path: Path, start: int, end: int) -> str:
    content = lines(path)
    end = min(end, len(content))
    return "\n".join(f"{idx:>5}: {content[idx - 1]}" for idx in range(start, end + 1))


status_path = EVIDENCE / "status.json"
status = json.loads(status_path.read_text(encoding="utf-8"))

# The archive directory was created before the first scripted status capture. This
# filtered capture isolates pre-existing paths from this run's artifacts.
filtered = subprocess.run(
    [
        "git",
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        ".",
        f":(exclude){OUT.relative_to(REPO)}",
    ],
    cwd=REPO,
    capture_output=True,
)
(LOGS / "git_preexisting_filtered.stdout").write_bytes(filtered.stdout)
(LOGS / "git_preexisting_filtered.stderr").write_bytes(filtered.stderr)
write_json(
    LOGS / "git_preexisting_filtered.json",
    {
        "cwd": str(REPO),
        "argv": ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", ".", f":(exclude){OUT.relative_to(REPO)}"],
        "exit_code": filtered.returncode,
        "note": "Captured after archive creation with this archive excluded; identifies unrelated pre-existing working-tree paths.",
    },
)

before = json.loads((EVIDENCE / "protected_hashes_before.json").read_text(encoding="utf-8"))
verification = []
for raw_path, expected in before.items():
    path = Path(raw_path)
    actual = sha256(path) if path.exists() else None
    verification.append({"path": raw_path, "before": expected, "after": actual, "unchanged": actual == expected})
write_json(EVIDENCE / "protected_hash_verification.json", verification)
protected_unchanged = all(item["unchanged"] for item in verification)

bpmn = OUT / "source_models" / "SupplyChainPaper.bpmn"
dmn = OUT / "source_models" / "supplyChainPaper.dmn"
pim = OUT / "pim" / "SupplyChainPaper.b2c"
go = OUT / "fabric" / "raw" / "SupplyChainPaper.go"
sol = OUT / "geth" / "raw" / "SupplyChainPaper.sol"

with (EVIDENCE / "input_checksums.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["archived_file", "original_path", "sha256", "byte_equal_to_original"])
    for archived, original in [
        (bpmn, REPO / "Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn"),
        (dmn, REPO / "Experiment/BPMNwithDMNcase/supplyChainPaper.dmn"),
    ]:
        writer.writerow([archived.relative_to(OUT), original, sha256(archived), archived.read_bytes() == original.read_bytes()])

trace_rows = [
    {
        "source_file_and_xml_id_or_field": "SupplyChainPaper.bpmn / Message_0rwz1km / numberOfUnits, urgent",
        "source_line": first_line(bpmn, '<bpmn2:message id="Message_0rwz1km"'),
        "b2cdsl_object_or_flow": "Message_0rwz1km schema; globals NumberOfUnits and Urgent",
        "b2cdsl_line": first_line(pim, "message Message_0rwz1km"),
        "generation_context_key_path": "fabric.globals[NumberOfUnits,Urgent]; fabric.flow_functions[Message_0rwz1km_Send]; geth.globals; geth.flow_functions",
        "fabric_file_function_and_line": ref(go, "func (cc *SmartContract) Message_0rwz1km_Send", "Message_0rwz1km_Send"),
        "solidity_file_function_and_line": ref(sol, "function Message_0rwz1km_Send", "Message_0rwz1km_Send"),
        "notes": "Message payload parameters are written to persistent global/state memory.",
    },
    {
        "source_file_and_xml_id_or_field": "SupplyChainPaper.bpmn / Message_0hpha6h / supplierReputation",
        "source_line": first_line(bpmn, '<bpmn2:message id="Message_0hpha6h"'),
        "b2cdsl_object_or_flow": "Message_0hpha6h schema; global SupplierReputation",
        "b2cdsl_line": first_line(pim, "message Message_0hpha6h"),
        "generation_context_key_path": "fabric.globals[SupplierReputation]; fabric.flow_functions[Message_0hpha6h_Send]; geth.globals; geth.flow_functions",
        "fabric_file_function_and_line": ref(go, "func (cc *SmartContract) Message_0hpha6h_Send", "Message_0hpha6h_Send"),
        "solidity_file_function_and_line": ref(sol, "function Message_0hpha6h_Send", "Message_0hpha6h_Send"),
        "notes": "Message payload is the third DMN input global.",
    },
    {
        "source_file_and_xml_id_or_field": "SupplyChainPaper.bpmn / Activity_0rm8bkp / inputs+output",
        "source_line": first_line(bpmn, '<bpmn2:businessRuleTask id="Activity_0rm8bkp"'),
        "b2cdsl_object_or_flow": "businessrule Activity_0rm8bkp mappings",
        "b2cdsl_line": first_line(pim, "businessrule Activity_0rm8bkp"),
        "generation_context_key_path": "fabric.business_rules[0], fabric.flow_functions; geth.business_rules[0], geth.flow_functions",
        "fabric_file_function_and_line": ref(go, "func (cc *SmartContract) Activity_0rm8bkp(", "Activity_0rm8bkp request"),
        "solidity_file_function_and_line": ref(sol, "function Activity_0rm8bkp(", "Activity_0rm8bkp request"),
        "notes": "Request functions collect three state-memory inputs and dispatch an external DMN evaluation.",
    },
    {
        "source_file_and_xml_id_or_field": "supplyChainPaper.dmn / decision_0tybghz, Decision_0zwjfyy, requiredDecision",
        "source_line": first_line(dmn, '<decision id="decision_0tybghz"'),
        "b2cdsl_object_or_flow": "No corresponding DMN decision ID; emitted Activity_0rm8bkp_DecisionID",
        "b2cdsl_line": first_line(pim, 'decision "Activity_0rm8bkp_DecisionID"'),
        "generation_context_key_path": "business rule configuration accepts a runtime decisionId; original DMN was not read",
        "fabric_file_function_and_line": ref(go, "Activity_0rm8bkp_DecisionID string", "InitParameter field"),
        "solidity_file_function_and_line": ref(sol, "string decisionId;", "BusinessRuleInit/BusinessRule runtime field"),
        "notes": "DMN XML declares the dependency; this run did not validate or execute that dependency.",
    },
    {
        "source_file_and_xml_id_or_field": "supplyChainPaper.dmn / finalPriority",
        "source_line": first_line(dmn, 'label="finalPriority"'),
        "b2cdsl_object_or_flow": "finalPriority -> FinalPriority",
        "b2cdsl_line": first_line(pim, "finalPriority -> FinalPriority"),
        "generation_context_key_path": "fabric.business_rules[0].done_actions and flow function; geth.business_rules[0].output_mappings and flow function",
        "fabric_file_function_and_line": ref(go, "func (cc *SmartContract) Activity_0rm8bkp_Continue", "Activity_0rm8bkp_Continue dynamic ParamMapping write-back"),
        "solidity_file_function_and_line": ref(sol, 'inst.stateMemory.FinalPriority = _extractJsonString(raw, "finalPriority")', "Activity_0rm8bkp_Continue"),
        "notes": "Go uses runtime ParamMapping plus reflection; Solidity has an explicit generated assignment.",
    },
    {
        "source_file_and_xml_id_or_field": "SupplyChainPaper.bpmn / Gateway_0ep8cuh / four finalPriority flows",
        "source_line": first_line(bpmn, 'sourceRef="Gateway_0ep8cuh" targetRef="ChoreographyTask_1573x71"'),
        "b2cdsl_object_or_flow": "Gateway_0ep8cuh choose Low/High/Medium/VeryLow",
        "b2cdsl_line": first_line(pim, "when gateway Gateway_0ep8cuh completed"),
        "generation_context_key_path": "fabric.flow_functions[Gateway_0ep8cuh]; geth.flow_functions[Gateway_0ep8cuh]",
        "fabric_file_function_and_line": ref(go, "func (cc *SmartContract) Gateway_0ep8cuh", "Gateway_0ep8cuh"),
        "solidity_file_function_and_line": ref(sol, "function Gateway_0ep8cuh", "Gateway_0ep8cuh"),
        "notes": "Branches enable Message_1oxmq1k, Message_1dmeexg, Message_1dzkcn0, and Message_0d2xte5 respectively.",
    },
    {
        "source_file_and_xml_id_or_field": "SupplyChainPaper.bpmn / Gateway_0onpe6x split and Gateway_1fbifca join",
        "source_line": first_line(bpmn, '<bpmn2:parallelGateway id="Gateway_0onpe6x"'),
        "b2cdsl_object_or_flow": "split to Message_0cba4t6+Message_0pm90nx; join awaits both; enables Message_0rwz1km",
        "b2cdsl_line": first_line(pim, "when gateway Gateway_0onpe6x completed"),
        "generation_context_key_path": "fabric.flow_functions[Gateway_0onpe6x,Gateway_1fbifca]; geth.flow_functions equivalents",
        "fabric_file_function_and_line": ref(go, "func (cc *SmartContract) Gateway_0onpe6x", "Gateway_0onpe6x / Gateway_1fbifca"),
        "solidity_file_function_and_line": ref(sol, "function Gateway_0onpe6x", "Gateway_0onpe6x / Gateway_1fbifca"),
        "notes": "Join predecessor set is exactly Message_0cba4t6 and Message_0pm90nx.",
    },
]
with (EVIDENCE / "traceability.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(trace_rows[0]))
    writer.writeheader()
    writer.writerows(trace_rows)

location_rows = [
    ("BPMN converter CLI", "generator_snapshot/src/newTranslator/generator/bpmn_to_dsl.py", "def main"),
    ("BPMN translator and type mapping", "generator_snapshot/src/newTranslator/generator/translator.py", "BPMN_TYPE_TO_DSL"),
    ("B2CDSL grammar", "generator_snapshot/src/newTranslator/DSL/B2CDSL/b2cdsl/b2c.tx", "BusinessRule"),
    ("Go renderer/context/type+state mapping", "generator_snapshot/src/newTranslator/CodeGenerator/b2cdsl-go/b2cdsl_go/__init__.py", "class GoChaincodeRenderer"),
    ("Go main template", "generator_snapshot/src/newTranslator/CodeGenerator/b2cdsl-go/templates/contract.go.jinja", ""),
    ("Solidity renderer/context/type+state mapping", "generator_snapshot/src/newTranslator/CodeGenerator/b2cdsl-solidity/b2cdsl_solidity/__init__.py", "class SolidityRenderer"),
    ("Solidity main template", "generator_snapshot/src/newTranslator/CodeGenerator/b2cdsl-solidity/templates/contract.sol.jinja", ""),
    ("Participant binding input", "generator_snapshot/src/newTranslator/generator/bindings.json", ""),
]
with (EVIDENCE / "source_locations.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["role", "snapshot_path", "line", "needle"])
    for role, rel, needle in location_rows:
        path = OUT / rel
        writer.writerow([role, rel, first_line(path, needle) if needle else 1, needle])

worked = [
    "# Worked mapping extracts",
    "",
    "Every block below is copied verbatim from an archived raw file, with archive-relative path and line numbers. It is evidence, not repaired pseudocode.",
    "",
    "## Message fields to globals/state memory",
    "",
    f"`source_models/SupplyChainPaper.bpmn:24`\n\n```xml\n{excerpt(bpmn, 24, 29)}\n```",
    "",
    f"`pim/SupplyChainPaper.b2c:52`\n\n```text\n{excerpt(pim, 52, 72)}\n```",
    "",
    f"`fabric/raw/SupplyChainPaper.go:1389`\n\n```go\n{excerpt(go, 1389, 1421)}\n```",
    "",
    f"`fabric/raw/SupplyChainPaper.go:1532`\n\n```go\n{excerpt(go, 1532, 1565)}\n```",
    "",
    f"`geth/raw/SupplyChainPaper.sol:1033`\n\n```solidity\n{excerpt(sol, 1033, 1045)}\n```",
    "",
    f"`geth/raw/SupplyChainPaper.sol:1064`\n\n```solidity\n{excerpt(sol, 1064, 1077)}\n```",
    "",
    "## Business rule and DMN binding evidence",
    "",
    f"`source_models/SupplyChainPaper.bpmn:158`\n\n```xml\n{excerpt(bpmn, 158, 164)}\n```",
    "",
    f"`source_models/supplyChainPaper.dmn:3` and `:70`\n\n```xml\n{excerpt(dmn, 3, 23)}\n...\n{excerpt(dmn, 70, 89)}\n```",
    "",
    f"`pim/SupplyChainPaper.b2c:177`\n\n```text\n{excerpt(pim, 177, 192)}\n```",
    "",
    "## Request, wait, continue, and output write-back",
    "",
    f"`fabric/raw/SupplyChainPaper.go:967`\n\n```go\n{excerpt(go, 967, 1020)}\n```",
    "",
    f"`fabric/raw/SupplyChainPaper.go:1042`\n\n```go\n{excerpt(go, 1042, 1074)}\n```",
    "",
    f"`fabric/raw/SupplyChainPaper.go:1081`\n\n```go\n{excerpt(go, 1081, 1130)}\n```",
    "",
    f"`geth/raw/SupplyChainPaper.sol:897`\n\n```solidity\n{excerpt(sol, 897, 972)}\n```",
    "",
    "## Rule completion and four priority branches",
    "",
    f"`pim/SupplyChainPaper.b2c:236`\n\n```text\n{excerpt(pim, 236, 255)}\n```",
    "",
    f"`fabric/raw/SupplyChainPaper.go:2111`\n\n```go\n{excerpt(go, 2111, 2130)}\n```",
    "",
    f"`geth/raw/SupplyChainPaper.sol:1196`\n\n```solidity\n{excerpt(sol, 1196, 1216)}\n```",
    "",
    "## Parallel split and join",
    "",
    f"`source_models/SupplyChainPaper.bpmn:80`\n\n```xml\n{excerpt(bpmn, 80, 116)}\n```",
    "",
    f"`pim/SupplyChainPaper.b2c:248`\n\n```text\n{excerpt(pim, 248, 252)}\n```",
    "",
    f"`geth/raw/SupplyChainPaper.sol:1219`\n\n```solidity\n{excerpt(sol, 1219, 1244)}\n```",
    "",
]
write_text(EVIDENCE / "worked_mapping_extracts.md", "\n".join(worked))

issues = f"""# Issues and limits

## Runtime errors

1. **Go compile: FAIL.** `fabric/raw/go.mod` requires Go 1.23.1, while the installed `/usr/local/go/bin/go` is 1.22.0. The first check with `GOTOOLCHAIN=local` rejected the version (`logs/B_go_compile.stderr`). A second check with `GOTOOLCHAIN=auto` attempted to download Go 1.23.1 but timed out at `proxy.golang.org` (`logs/B_go_compile_auto.stderr`). This is an environment/toolchain failure; it is not evidence that the generated Go code compiles or fails at the source level.

## Static observations

1. **The supplied DMN was not read by BPMN→DSL.** `generation_contexts/A_file_reads.json` records the Python audit events for the sidecar rerun. It includes `SupplyChainPaper.bpmn` and `generator/bindings.json`, but not `supplyChainPaper.dmn`. The Go and Solidity generation read audits likewise consume the generated B2CDSL and generator assets, not the supplied DMN.
2. **The emitted binding does not match the DMN IDs.** Raw B2CDSL lines 178–179 contain `Activity_0rm8bkp.dmn` and `Activity_0rm8bkp_DecisionID`, synthesized in `generator/translator.py`. The supplied file is `supplyChainPaper.dmn`, whose decisions are `decision_0tybghz` and `Decision_0zwjfyy`. No correction was applied.
3. **The two-decision dependency is declared, not executed here.** The DMN XML contains `Decision_0zwjfyy` → `requiredDecision href=\"#decision_0tybghz\"`. Generated platform code accepts runtime DMN content/CID and a decision ID. No engine/network was run, so dependency support and the correct decision-selection behavior remain unverified.
4. **Bindings partly come from BPMN and partly from defaults/runtime parameters.** Input/output mappings come from the BPMN business-rule documentation. Participant MSP/attributes come from `generator/bindings.json` when present, otherwise name-derived defaults. Go receives DMN content, decision ID, and ParamMapping in init parameters; Solidity receives CID, decision ID, caller, and evaluation endpoint through initialization structures.
5. **The diagnostic context is not a native PSM.** `generation_contexts/*.context*.json` and `geth.execution_layout.diagnostic.json` are sidecar dumps made by wrapping the original renderers. The native/sidecar outputs are byte-identical according to `generation_contexts/native_sidecar_comparison.json`.
6. **Case constructs.** The model contains a parallel split (`Gateway_0onpe6x`) and join (`Gateway_1fbifca`) with predecessor set `Message_0cba4t6`, `Message_0pm90nx`. It contains no event-based gateway, Oracle receive/script task, or dual-message choreography task; no such constructs were fabricated.

## Unverified risks and absent artifacts

1. Chain deployment and transaction execution were intentionally NOT_RUN. External Fabric Oracle/DMNEngine behavior, Geth `IDmnLite` behavior, participant accounts/organizations, CID/content, initialization values, and the actual DMN response shape were not validated.
2. The generator did not emit a native FFI. Solidity ABI and bytecode in `geth/compiled/` were produced by the compile check, and execution layout exists only as a diagnostic dump. No absent FFI was synthesized.
3. Solidity compiled successfully with installed solc-js 0.8.33. That proves compiler acceptance only, not deployment or runtime correctness.
4. `existing_artifacts/` contains historical candidates confirmed by both distinctive BPMN IDs or both DMN decision IDs. This correspondence identifies the case family; it does not certify byte equivalence to the current source models.
"""
write_text(EVIDENCE / "issues.md", issues)

existing_readme = """# Existing artifacts

These files are historical references copied with their repository-relative paths. The search used the filename plus the distinctive identifiers `Activity_0rm8bkp`, `Gateway_0ep8cuh`, `decision_0tybghz`, and `Decision_0zwjfyy`. A file was copied only when it contained both BPMN identifiers or both DMN decision identifiers. See `../evidence/historical_candidates.json` for every candidate, its hits, SHA-256, and whether it was archived.

The copied files are not treated as products of this run and do not substitute for `pim/`, `fabric/raw/`, or `geth/raw/`.
"""
write_text(OUT / "existing_artifacts" / "README.md", existing_readme)

status_evidence = {
    "input_check": "evidence/input_checksums.csv; archived files byte-equal",
    "bpmn_to_dsl": "logs/A_bpmn_to_dsl.json; pim/SupplyChainPaper.b2c",
    "dsl_parse": "logs/A_parse.json",
    "go_generation": "logs/B_go_generate.json; fabric/raw/",
    "solidity_generation": "logs/C_solidity_generate.json; geth/raw/SupplyChainPaper.sol",
    "context_export": "logs/D_diagnostic.json; generation_contexts/native_sidecar_comparison.json",
    "go_compile": "logs/B_go_compile.json and logs/B_go_compile_auto.json",
    "solidity_compile": "logs/C_solidity_compile.json; geth/compiled/",
    "onchain_execution": "out of scope; no deployment or transactions",
}

readme = f"""# SupplyChainPaper reproduction archive

This archive records an unmodified run of the local ChainCollab conversion chain at branch `release-MultiBlockchain`, commit `8321eef08c96e78f2bac67eec19bb4d566418841`. It separates new raw products from historical references and diagnostic sidecars.

| Stage | Status | Evidence |
|---|---|---|
| Input files checked | {status['input_check']} | {status_evidence['input_check']} |
| BPMN → B2CDSL | {status['bpmn_to_dsl']} | {status_evidence['bpmn_to_dsl']} |
| B2CDSL grammar parse | {status['dsl_parse']} | {status_evidence['dsl_parse']} |
| B2CDSL → Fabric/Go | {status['go_generation']} | {status_evidence['go_generation']} |
| B2CDSL → Geth/Solidity | {status['solidity_generation']} | {status_evidence['solidity_generation']} |
| Generation-context export | {status['context_export']} | {status_evidence['context_export']} |
| Go compile | {status['go_compile']} | {status_evidence['go_compile']} |
| Solidity compile | {status['solidity_compile']} | {status_evidence['solidity_compile']} |
| Chain deployment/execution | {status['onchain_execution']} | {status_evidence['onchain_execution']} |

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

Protected input and generator snapshot source hashes are unchanged: **{str(protected_unchanged).lower()}** (`evidence/protected_hash_verification.json`). No source model, generator, grammar, renderer, or template was edited. `logs/git_preexisting_filtered.stdout` records unrelated pre-existing untracked files with this archive excluded. The archive itself is an untracked output under `artifacts/`.

`manifest.csv` lists archive-relative paths, origins/commands, stages, file nature, and SHA-256. It excludes itself because a stable self-hash is impossible. `reproduce.sh` refuses to overwrite an existing target and reruns into a new directory.
"""
write_text(OUT / "README.md", readme)

for executable in [OUT / "reproduce.sh", OUT / "scripts" / "run_archive.py", OUT / "scripts" / "diagnostic.py", OUT / "scripts" / "run_checks.py", OUT / "scripts" / "finalize_archive.py"]:
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def classify(rel: Path) -> tuple[str, str, str]:
    text = rel.as_posix()
    if text.startswith("source_models/"):
        original = REPO / "Experiment/BPMNwithDMNcase" / rel.name
        return "inputs", "source", str(original)
    if text == "existing_artifacts/README.md":
        return "historical search", "diagnostic", "scripts/finalize_archive.py"
    if text.startswith("existing_artifacts/"):
        return "historical search", "historical", str(REPO / Path(*rel.parts[1:]))
    if text.startswith("pim/"):
        return "BPMN→B2CDSL", "generated", "python generator/bpmn_to_dsl.py SupplyChainPaper.bpmn -o pim/SupplyChainPaper.b2c"
    if text.startswith("fabric/raw/"):
        return "B2CDSL→Fabric/Go", "generated", "textx generate pim/SupplyChainPaper.b2c --target go --overwrite -o fabric/raw"
    if text.startswith("fabric/compile_copy/") or text.startswith("fabric/build_cache/"):
        return "Go compile", "diagnostic", "copy of fabric/raw used only for go build"
    if text.startswith("geth/raw/"):
        return "B2CDSL→Geth/Solidity", "generated", "python generator/b2c_to_solidity.py pim/SupplyChainPaper.b2c -o geth/raw/SupplyChainPaper.sol"
    if text.startswith("geth/compiled/"):
        return "Solidity compile", "generated", "solc-js 0.8.33 --bin --abi --optimize"
    if text.startswith("generation_contexts/"):
        return "generation-context sidecar", "diagnostic", "scripts/diagnostic.py; original APIs wrapped without changing returned context"
    if text.startswith("generator_snapshot/"):
        return "generator snapshot", "configuration", str(REPO / Path(*rel.parts[1:]))
    if text.startswith("logs/"):
        return "run log", "log", "stage command; see same-basename JSON for cwd/argv/exit code"
    if text.startswith("evidence/"):
        return "evidence", "diagnostic", "scripts/finalize_archive.py"
    if text.startswith("scripts/") or text == "reproduce.sh":
        return "reproduction support", "configuration", "created for this archive"
    if text == "README.md":
        return "index", "diagnostic", "scripts/finalize_archive.py"
    return "archive", "diagnostic", "this run"


manifest_path = OUT / "manifest.csv"
with manifest_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["relative_path", "origin_path_or_generation_command", "stage", "file_nature", "sha256"])
    for path in sorted(item for item in OUT.rglob("*") if item.is_file() and item != manifest_path):
        rel = path.relative_to(OUT)
        stage, nature, origin = classify(rel)
        writer.writerow([rel.as_posix(), origin, stage, nature, sha256(path)])

zip_path = OUT.with_suffix(".zip")
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(item for item in OUT.rglob("*") if item.is_file()):
        archive.write(path, Path(OUT.name) / path.relative_to(OUT))

write_text(zip_path.with_suffix(".zip.sha256"), f"{sha256(zip_path)}  {zip_path.name}\n")
print(f"archive={OUT}")
print(f"zip={zip_path}")
print(f"protected_unchanged={protected_unchanged}")
print(json.dumps(status, ensure_ascii=False))
