#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from run_supplychainpaper_demo import EXP_DIR, ROOT, safe_case_name
from tag_utils import write_json


DEFAULT_BPMN_DIR = ROOT / "Experiment/BPMNwithDMNcase"
DEFAULT_OUT_DIR = EXP_DIR / "cases"
CASE_RUNNER = EXP_DIR / "scripts/run_supplychainpaper_demo.py"


def read_structural_status(case_dir: Path) -> str:
    summary_file = case_dir / "reports/structure_summary.json"
    if not summary_file.exists():
        return "ERROR"
    try:
        return json.loads(summary_file.read_text(encoding="utf-8")).get("structural_status", "ERROR")
    except json.JSONDecodeError:
        return "ERROR"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bpmn-dir", type=Path, default=DEFAULT_BPMN_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    bpmn_files = sorted(args.bpmn_dir.glob("*.bpmn"))
    if not bpmn_files:
        print(f"No BPMN files found in {args.bpmn_dir}")
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for bpmn_file in bpmn_files:
        case_name = safe_case_name(bpmn_file.stem)
        case_dir = args.out_dir / case_name
        cmd = [
            sys.executable,
            str(CASE_RUNNER),
            "--bpmn-file",
            str(bpmn_file),
            "--case-name",
            case_name,
            "--out-dir",
            str(case_dir),
        ]
        print("\n=== Running case:", bpmn_file.name, "as", case_name, "===")
        completed = subprocess.run(cmd, cwd=str(ROOT), text=True)
        status = read_structural_status(case_dir)
        if completed.returncode != 0 and status == "ERROR":
            status = "ERROR"
        results.append(
            {
                "case_name": case_name,
                "bpmn_file": str(bpmn_file),
                "case_dir": str(case_dir),
                "returncode": completed.returncode,
                "structural_status": status,
                "summary": str(case_dir / "reports/structure_summary.md"),
            }
        )

    passed = sum(1 for item in results if item["structural_status"] == "PASS")
    failed = sum(1 for item in results if item["structural_status"] == "FAIL")
    errored = len(results) - passed - failed
    batch_summary = {
        "bpmn_dir": str(args.bpmn_dir),
        "out_dir": str(args.out_dir),
        "total_cases": len(results),
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "cases": results,
    }
    write_json(args.out_dir / "batch_summary.json", batch_summary)

    lines = [
        "# Experiment 1B Batch Summary",
        "",
        f"BPMN directory: `{args.bpmn_dir}`",
        f"Output directory: `{args.out_dir}`",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| total_cases | {len(results)} |",
        f"| passed | {passed} |",
        f"| failed | {failed} |",
        f"| errored | {errored} |",
        "",
        "| Case | Status | Return Code | Summary |",
        "|---|---|---:|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['case_name']} | {item['structural_status']} | {item['returncode']} | `{item['summary']}` |"
        )
    (args.out_dir / "batch_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nBatch summary: {args.out_dir / 'batch_summary.md'}")
    return 0 if errored == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
