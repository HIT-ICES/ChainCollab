#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Sequence

from common import CHAINCOLLAB_ROOT, EXP3_ROOT, dump_json, dump_text, load_json
from parse_b2c import parse_b2c_model


DEFAULT_PYTHON = str(CHAINCOLLAB_ROOT / "src" / "newTranslator" / ".venv" / "bin" / "python")


def load_model(path: Path) -> Dict[str, Any]:
    if path.suffix == ".json":
        return load_json(path)
    return parse_b2c_model(path)


def run_command(cmd: Sequence[str], *, label: str, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"\n== {label} ==")
    print(" ".join(cmd))
    result = subprocess.run(
        list(cmd),
        cwd=str(CHAINCOLLAB_ROOT),
        text=True,
        check=False,
    )
    if result.returncode != 0 and not allow_failure:
        raise subprocess.CalledProcessError(result.returncode, list(cmd))
    return result


def latest_replay(replays_dir: Path) -> Path:
    candidates = sorted(replays_dir.glob("replay_*.json"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No replay JSON found under {replays_dir}")
    return candidates[-1]


def start_event_steps(model: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    for flow in model.get("flows", []) or []:
        if flow.get("kind") != "start_flow":
            continue
        trigger = flow.get("trigger") or {}
        element = trigger.get("name")
        if element:
            steps.append({"type": "event", "element": element})
    return steps


def parallel_join_steps(model: Dict[str, Any]) -> List[Dict[str, Any]]:
    joins: List[Dict[str, Any]] = []
    for flow in model.get("flows", []) or []:
        if flow.get("kind") != "parallel_join":
            continue
        trigger = flow.get("trigger") or {}
        element = trigger.get("name")
        if not element:
            continue
        sources: List[str] = []
        for condition in flow.get("conditions", []) or []:
            for source in condition.get("sources", []) or []:
                if source not in sources:
                    sources.append(source)
        joins.append({"type": "gateway", "element": element, "sources": sources})
    return joins


def with_solidity_businessrule_payloads(step: Dict[str, Any]) -> Dict[str, Any]:
    item = deepcopy(step)
    if item.get("type") == "businessrule":
        item.setdefault("payload", {})
        item.setdefault("continue_payload", {})
    return item


def build_logical_path(generated_path: Dict[str, Any], *, case_name: str, model_path: Path, model: Dict[str, Any]) -> Dict[str, Any]:
    body_steps = [with_solidity_businessrule_payloads(step) for step in deepcopy(generated_path.get("steps") or [])]

    existing_elements = {str(step.get("element") or "") for step in body_steps}
    insertions: List[tuple[int, Dict[str, Any]]] = []
    for join in parallel_join_steps(model):
        gateway = str(join["element"])
        if gateway in existing_elements:
            continue
        source_positions = [
            index
            for index, step in enumerate(body_steps)
            if str(step.get("element") or "") in set(join.get("sources") or [])
        ]
        if source_positions and len(source_positions) == len(set(join.get("sources") or [])):
            insertions.append((max(source_positions) + 1, {"type": "gateway", "element": gateway}))

    for index, step in sorted(insertions, key=lambda item: item[0], reverse=True):
        body_steps.insert(index, step)

    steps = start_event_steps(model) + body_steps
    return {
        "case_name": case_name,
        "path_name": generated_path.get("path_name"),
        "description": "Auto materialized from generated DSL executable path.",
        "source_model": str(model_path),
        "expect": generated_path.get("expect", "accepted"),
        "steps": steps,
        "generated_path": {
            "final_enabled_elements": generated_path.get("final_enabled_elements", []),
            "final_element_states": generated_path.get("final_element_states", {}),
            "final_globals": generated_path.get("final_globals", {}),
        },
    }


def path_matches(path_spec: Dict[str, Any], filters: set[str]) -> bool:
    if not filters:
        return True
    name = str(path_spec.get("path_name") or "")
    elements = [str(step.get("element") or "") for step in path_spec.get("steps") or []]
    outputs = " ".join(
        str(value)
        for step in path_spec.get("steps") or []
        for value in (step.get("outputs") or {}).values()
    )
    haystack = " ".join([name, *elements, outputs]).lower()
    return all(item.lower() in haystack for item in filters)


def normalize_and_compare(
    *,
    python_bin: str,
    dsl_trace: Path,
    dsl_model: Path,
    replay_json: Path,
    dsl_normalized: Path,
    solidity_normalized: Path,
    comparison_json: Path,
    comparison_md: Path,
) -> subprocess.CompletedProcess[str]:
    run_command(
        [
            python_bin,
            str(EXP3_ROOT / "scripts" / "normalize_traces.py"),
            "--platform",
            "dsl",
            "--trace",
            str(dsl_trace),
            "--model",
            str(dsl_model),
            "--output",
            str(dsl_normalized),
        ],
        label="Normalize DSL trace",
    )
    run_command(
        [
            python_bin,
            str(EXP3_ROOT / "scripts" / "normalize_traces.py"),
            "--platform",
            "solidity",
            "--trace",
            str(replay_json),
            "--model",
            str(dsl_model),
            "--output",
            str(solidity_normalized),
        ],
        label="Normalize Solidity trace",
    )
    return run_command(
        [
            sys.executable,
            str(EXP3_ROOT / "scripts" / "compare_normalized_traces.py"),
            "--left",
            str(dsl_normalized),
            "--right",
            str(solidity_normalized),
            "--output-json",
            str(comparison_json),
            "--output-md",
            str(comparison_md),
        ],
        label="Compare normalized traces",
        allow_failure=True,
    )


def write_summary(case_name: str, entries: List[Dict[str, Any]]) -> None:
    summary_dir = EXP3_ROOT / "outputs" / case_name
    payload = {
        "case_name": case_name,
        "path_count": len(entries),
        "paths": entries,
    }
    dump_json(summary_dir / "pipeline_summary.json", payload)

    lines = [
        f"# {case_name} Pipeline Summary",
        "",
        "| Path | Status | Comparison | Replay |",
        "| --- | --- | --- | --- |",
    ]
    for entry in entries:
        comparison = entry.get("consistent")
        comparison_text = "skipped" if comparison is None else str(comparison)
        replay = entry.get("replay_json") or ""
        lines.append(
            f"| `{entry.get('path_name')}` | `{entry.get('status')}` | `{comparison_text}` | `{replay}` |"
        )
    dump_text(summary_dir / "pipeline_summary.md", "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate all paths for one exp3 case and run each path through DSL, Solidity, normalization, and comparison."
    )
    parser.add_argument("--case-name", required=True, help="Case name, e.g. SupplyChainPaper")
    parser.add_argument("--model", required=True, help="Path to the case .b2c or parsed dsl_model.json")
    parser.add_argument("--solidity-config", required=True, help="Per-case Solidity replay config JSON")
    parser.add_argument("--python", default=DEFAULT_PYTHON, help="Python interpreter for exp3 DSL scripts")
    parser.add_argument("--max-depth", type=int, default=64)
    parser.add_argument("--max-paths", type=int, default=1000)
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Optional filter token. Can be repeated; path name/elements/outputs must contain all tokens.",
    )
    parser.add_argument("--skip-solidity", action="store_true", help="Reuse latest replay JSON under each path's replays dir")
    parser.add_argument("--skip-compare", action="store_true", help="Stop after DSL/Solidity raw outputs")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue remaining paths after a path fails")
    args = parser.parse_args()

    case_name = args.case_name
    model_path = Path(args.model).resolve()
    solidity_config = Path(args.solidity_config).resolve()
    if not model_path.exists():
        raise SystemExit(f"Model not found: {model_path}")
    if not solidity_config.exists():
        raise SystemExit(f"Solidity config not found: {solidity_config}")

    case_dir = EXP3_ROOT / "cases" / case_name
    generated_paths_file = case_dir / "generated_paths.json"
    model = load_model(model_path)

    run_command(
        [
            args.python,
            str(EXP3_ROOT / "scripts" / "generate_dsl_paths.py"),
            "--model",
            str(model_path),
            "--case-name",
            case_name,
            "--output",
            str(generated_paths_file),
            "--max-depth",
            str(args.max_depth),
            "--max-paths",
            str(args.max_paths),
        ],
        label="Generate all executable DSL paths",
    )

    generated = load_json(generated_paths_file)
    generated_paths = [
        path
        for path in generated.get("paths", [])
        if path_matches(path, set(args.only))
    ]
    if not generated_paths:
        raise SystemExit("No generated path matched the requested filters.")

    summary: List[Dict[str, Any]] = []
    for index, generated_path in enumerate(generated_paths, start=1):
        path_name = str(generated_path.get("path_name") or f"{case_name}_path_{index:03d}")
        print(f"\n\n######## Path {index}/{len(generated_paths)}: {path_name} ########")

        case_path_dir = case_dir / "paths" / path_name
        dsl_path_dir = EXP3_ROOT / "dsl" / case_name / "paths" / path_name
        solidity_path_dir = EXP3_ROOT / "solidity" / case_name / "paths" / path_name
        output_path_dir = EXP3_ROOT / "outputs" / case_name / "paths" / path_name
        normalized_dir = output_path_dir / "normalized"

        logical_path = case_path_dir / "logical_path.json"
        dsl_case = dsl_path_dir / "case.json"
        execution_sequence = solidity_path_dir / "execution_sequence.json"
        dsl_trace = dsl_path_dir / "dsl_trace.json"
        dsl_model = dsl_path_dir / "dsl_model.json"
        replays_dir = solidity_path_dir / "replays"
        dsl_normalized = normalized_dir / "dsl.normalized.json"
        solidity_normalized = normalized_dir / "solidity.normalized.json"
        comparison_json = output_path_dir / "comparison.json"
        comparison_md = output_path_dir / "comparison.md"

        entry: Dict[str, Any] = {
            "path_name": path_name,
            "logical_path": str(logical_path),
            "dsl_case": str(dsl_case),
            "execution_sequence": str(execution_sequence),
            "status": "started",
        }
        try:
            logical = build_logical_path(generated_path, case_name=case_name, model_path=model_path, model=model)
            dump_json(logical_path, logical)

            run_command(
                [
                    args.python,
                    str(EXP3_ROOT / "scripts" / "materialize_logical_path.py"),
                    "--logical-path",
                    str(logical_path),
                    "--model",
                    str(model_path),
                    "--dsl-case-output",
                    str(dsl_case),
                    "--solidity-sequence-output",
                    str(execution_sequence),
                ],
                label="Materialize logical path",
            )

            run_command(
                [
                    args.python,
                    str(EXP3_ROOT / "scripts" / "run_exp3.py"),
                    "--case-file",
                    str(dsl_case),
                ],
                label="Run DSL simulator",
            )

            if args.skip_solidity:
                print("\n== Run Solidity/Geth replay ==")
                print("Skipped; reusing latest replay.")
            else:
                run_command(
                    [
                        sys.executable,
                        str(EXP3_ROOT / "scripts" / "replay_bound_eth_instance.py"),
                        "--config",
                        str(solidity_config),
                        "--sequence-file",
                        str(execution_sequence),
                    ],
                    label="Run Solidity/Geth replay",
                )

            replay_json = latest_replay(replays_dir)
            entry["replay_json"] = str(replay_json)

            if not args.skip_compare:
                compare_result = normalize_and_compare(
                    python_bin=args.python,
                    dsl_trace=dsl_trace,
                    dsl_model=dsl_model,
                    replay_json=replay_json,
                    dsl_normalized=dsl_normalized,
                    solidity_normalized=solidity_normalized,
                    comparison_json=comparison_json,
                    comparison_md=comparison_md,
                )
                if comparison_json.exists():
                    comparison = load_json(comparison_json)
                    entry["consistent"] = bool(comparison.get("consistent"))
                    entry["finding_count"] = comparison.get("finding_count")
                entry["status"] = "completed" if compare_result.returncode == 0 else "comparison_failed"
            else:
                entry["status"] = "completed_without_compare"
        except Exception as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
            summary.append(entry)
            write_summary(case_name, summary)
            if not args.continue_on_error:
                raise
            print(f"Path failed, continuing: {exc}")
            continue

        summary.append(entry)
        write_summary(case_name, summary)

    print(f"\nPipeline finished for {case_name}.")
    print(f"Summary JSON: {EXP3_ROOT / 'outputs' / case_name / 'pipeline_summary.json'}")
    print(f"Summary Markdown: {EXP3_ROOT / 'outputs' / case_name / 'pipeline_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
