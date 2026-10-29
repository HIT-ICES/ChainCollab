#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from common import EXP3_ROOT, dump_json, dump_text, load_json
from dsl_simulator import DSLSimulator
from parse_b2c import parse_b2c_model


def discover_case_dirs(cases_dir: Path) -> List[Path]:
    return sorted(path for path in cases_dir.iterdir() if path.is_dir() and (path / "case.json").exists())


def discover_dsl_case_files() -> List[Path]:
    return sorted((EXP3_ROOT / "dsl").glob("*/paths/*/case.json"))


def resolve_b2c_path(case_dir: Path, manifest: Dict[str, Any]) -> Path:
    configured = manifest.get("source_b2c")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else (case_dir / configured).resolve()
    local = case_dir / "input.b2c"
    if local.exists():
        return local
    raise FileNotFoundError(f"No DSL source configured for case {case_dir.name}")


def run_case_file(case_file: Path) -> Dict[str, Any]:
    manifest = load_json(case_file)
    case_dir = case_file.parent
    case_name = manifest.get("case_name", case_dir.name)
    b2c_path = resolve_b2c_path(case_dir, manifest)
    model = parse_b2c_model(b2c_path)

    path_summaries: List[Dict[str, Any]] = []
    report_lines = [f"# {case_name}", "", manifest.get("description", ""), "", "## Paths", ""]

    for path_spec in manifest.get("paths", []):
        path_name = path_spec["path_name"]
        output_dir = EXP3_ROOT / "dsl" / case_name / "paths" / path_name
        simulator = DSLSimulator(model, case_name)
        trace = simulator.run_path(path_spec)
        dump_json(output_dir / "path.json", path_spec)
        dump_json(output_dir / "dsl_model.json", model)
        dump_json(output_dir / "dsl_trace.json", trace)
        path_summaries.append(
            {
                "path_name": path_name,
                "expected": path_spec.get("expect", "accepted"),
                "actual": trace["final_state"]["status"],
                "reason": trace["final_state"].get("reason", ""),
            }
        )
        report_lines.append(f"- `{path_spec['path_name']}`: expected `{path_spec.get('expect', 'accepted')}`, actual `{trace['final_state']['status']}`")
        if trace["final_state"].get("reason"):
            report_lines.append(f"  reason: {trace['final_state']['reason']}")

    report_lines.extend(["", "## Notes", "", "- This phase runs only the DSL reference simulator.", "- Go/Fabric and Solidity execution hooks are intentionally deferred to the next phase."])
    dump_text(EXP3_ROOT / "dsl" / case_name / "report.md", "\n".join(report_lines) + "\n")

    return {"case_name": case_name, "source_b2c": str(b2c_path), "paths": path_summaries}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exp3 DSL-only reference simulation.")
    parser.add_argument("--case", default="all", help="Case directory name under exp3/cases, or 'all'")
    parser.add_argument("--case-file", default="", help="Explicit platform-specific DSL case.json path")
    args = parser.parse_args()

    if args.case_file:
        case_files = [Path(args.case_file).resolve()]
    else:
        case_files = discover_dsl_case_files()
        if args.case != "all":
            case_files = [
                path for path in case_files
                if path.parents[2].name == args.case
            ]
        if not case_files:
            raise SystemExit(f"No cases found for selector: {args.case}")

    summary = {"phase": "dsl_reference_only", "cases": [run_case_file(case_file) for case_file in case_files]}
    dump_json(EXP3_ROOT / "outputs" / "summary.json", summary)

    lines = ["# Exp3 Summary", "", "- Current phase: DSL reference simulator only", ""]
    for case in summary["cases"]:
        lines.append(f"## {case['case_name']}")
        lines.append("")
        for path in case["paths"]:
            lines.append(f"- `{path['path_name']}`: expected `{path['expected']}`, actual `{path['actual']}`")
        lines.append("")
    dump_text(EXP3_ROOT / "outputs" / "summary.md", "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
