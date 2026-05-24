#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/code/ChainCollab")
EXP1B_DIR = ROOT / "Experiment/new/exp1_1B"
ADDITION_DIR = EXP1B_DIR / "Addition"
EXP3_CASES_DIR = ROOT / "Experiment/new/exp3/cases"
EXP1B_CASES_DIR = EXP1B_DIR / "cases"
CHECKER = ADDITION_DIR / "scripts/check_exp3_path_traceability.py"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_case_status(case_out: Path) -> tuple[str, dict[str, Any]]:
    report_file = case_out / "path_traceability_report.json"
    if not report_file.exists():
        return "ERROR", {}
    try:
        report = read_json(report_file)
    except json.JSONDecodeError:
        return "ERROR", {}
    return report.get("exp3_path_traceability_status", "ERROR"), report


def write_batch_markdown(summary: dict[str, Any], output_file: Path) -> None:
    lines = [
        "# 1B Addition Batch Summary",
        "",
        f"Exp3 cases directory: `{summary['exp3_cases_dir']}`",
        f"1B cases directory: `{summary['exp1b_cases_dir']}`",
        f"Output directory: `{summary['out_dir']}`",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| total_cases | {summary['total_cases']} |",
        f"| passed | {summary['passed']} |",
        f"| failed | {summary['failed']} |",
        f"| errored | {summary['errored']} |",
        f"| logical_paths | {summary['logical_paths']} |",
        f"| logical_path_steps | {summary['logical_path_steps']} |",
        f"| traceable_logical_path_steps | {summary['traceable_logical_path_steps']} |",
        f"| untraceable_logical_path_steps | {summary['untraceable_logical_path_steps']} |",
        f"| overall_path_traceability | {summary['overall_path_traceability']:.4f} |",
        "",
        "| Case | Status | Paths | Steps | Traceability | Summary |",
        "|---|---|---:|---:|---:|---|",
    ]
    for case in summary["cases"]:
        lines.append(
            f"| {case['case_name']} | {case['status']} | {case['logical_paths']} | "
            f"{case['logical_path_steps']} | {case['overall_path_traceability']:.4f} | "
            f"`{case['summary_file']}` |"
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp3-cases-dir", type=Path, default=EXP3_CASES_DIR)
    parser.add_argument("--exp1b-cases-dir", type=Path, default=EXP1B_CASES_DIR)
    parser.add_argument("--out-dir", type=Path, default=ADDITION_DIR / "cases")
    args = parser.parse_args()

    exp3_cases = sorted(path for path in args.exp3_cases_dir.iterdir() if path.is_dir())
    results: list[dict[str, Any]] = []

    for exp3_case in exp3_cases:
        case_name = exp3_case.name
        logical_paths_dir = exp3_case / "paths"
        dsl_tag = args.exp1b_cases_dir / case_name / "dsl/dsl_tag.json"
        trace = args.exp1b_cases_dir / case_name / "trace/bpmn_dsl_trace.json"
        case_out = args.out_dir / case_name
        if not logical_paths_dir.exists() or not dsl_tag.exists() or not trace.exists():
            report = {
                "case_name": case_name,
                "exp3_path_traceability_status": "ERROR",
                "logical_paths_dir": str(logical_paths_dir),
                "dsl_tag": str(dsl_tag),
                "trace": str(trace),
                "error": "Missing logical paths directory, dsl_tag, or trace.",
            }
            write_json(case_out / "path_traceability_report.json", report)
            status = "ERROR"
            completed_returncode = 1
        else:
            cmd = [
                sys.executable,
                str(CHECKER),
                "--case-name",
                case_name,
                "--logical-paths-dir",
                str(logical_paths_dir),
                "--dsl-tag",
                str(dsl_tag),
                "--trace",
                str(trace),
                "--out-dir",
                str(case_out),
            ]
            print("+ " + " ".join(cmd))
            completed = subprocess.run(cmd, cwd=str(ROOT), text=True)
            completed_returncode = completed.returncode
            status, report = read_case_status(case_out)

        status, report = read_case_status(case_out)
        results.append(
            {
                "case_name": case_name,
                "status": status,
                "returncode": completed_returncode,
                "logical_paths": report.get("logical_paths", 0),
                "logical_path_steps": report.get("logical_path_steps", 0),
                "traceable_logical_path_steps": report.get("traceable_logical_path_steps", 0),
                "untraceable_logical_path_steps": report.get("untraceable_logical_path_steps", 0),
                "overall_path_traceability": report.get("overall_path_traceability", 0.0),
                "report_file": str(case_out / "path_traceability_report.json"),
                "summary_file": str(case_out / "path_traceability_summary.md"),
            }
        )

    total_steps = sum(item["logical_path_steps"] for item in results)
    traceable_steps = sum(item["traceable_logical_path_steps"] for item in results)
    untraceable_steps = sum(item["untraceable_logical_path_steps"] for item in results)
    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = sum(1 for item in results if item["status"] == "FAIL")
    errored = len(results) - passed - failed
    summary = {
        "exp3_cases_dir": str(args.exp3_cases_dir),
        "exp1b_cases_dir": str(args.exp1b_cases_dir),
        "out_dir": str(args.out_dir),
        "total_cases": len(results),
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "logical_paths": sum(item["logical_paths"] for item in results),
        "logical_path_steps": total_steps,
        "traceable_logical_path_steps": traceable_steps,
        "untraceable_logical_path_steps": untraceable_steps,
        "overall_path_traceability": traceable_steps / total_steps if total_steps else 1.0,
        "cases": results,
    }
    write_json(args.out_dir / "addition_batch_summary.json", summary)
    write_batch_markdown(summary, args.out_dir / "addition_batch_summary.md")
    print(f"\nAddition batch summary: {args.out_dir / 'addition_batch_summary.md'}")
    return 0 if failed == 0 and errored == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
