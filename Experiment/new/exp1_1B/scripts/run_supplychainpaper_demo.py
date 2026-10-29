#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from tag_utils import write_json


ROOT = Path("/root/code/ChainCollab")
EXP_DIR = ROOT / "Experiment/new/exp1_1B"
SCRIPTS = EXP_DIR / "scripts"
DEFAULT_BPMN = ROOT / "Experiment/BPMNwithDMNcase/SupplyChainPaper.bpmn"
DEFAULT_TRANSLATOR = ROOT / "src/newTranslator"
DEFAULT_TRANSLATOR_PYTHON = DEFAULT_TRANSLATOR / ".venv/bin/python"


def safe_case_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    if not cleaned:
        return "Case"
    if cleaned[0].isdigit():
        return f"Case_{cleaned}"
    return cleaned


def run(cmd: list[str], cwd: Path | None = None, allow_fail: bool = False) -> subprocess.CompletedProcess:
    print("+ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd or ROOT), text=True)
    if result.returncode != 0 and not allow_fail:
        raise SystemExit(result.returncode)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bpmn-file", type=Path, default=DEFAULT_BPMN)
    parser.add_argument("--case-name")
    parser.add_argument("--translator-root", type=Path, default=DEFAULT_TRANSLATOR)
    parser.add_argument("--translator-python", type=Path, default=DEFAULT_TRANSLATOR_PYTHON)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    args.case_name = args.case_name or safe_case_name(args.bpmn_file.stem)
    args.out_dir = args.out_dir or EXP_DIR / "cases" / args.case_name
    out = args.out_dir
    bpmn_out = out / "bpmn"
    dsl_out = out / "dsl"
    trace_out = out / "trace"
    reports_out = out / "reports"
    dsl_file = out / "dsl" / f"{args.case_name}.b2c"
    contract_file = EXP_DIR / "contracts/default_mapping_contract.json"

    out.mkdir(parents=True, exist_ok=True)
    write_json(
        out / "input_index.json",
        {
            "case_name": args.case_name,
            "bpmn_file": str(args.bpmn_file),
            "dsl_file": str(dsl_file),
            "mapping_contract": str(contract_file),
            "translator_root": str(args.translator_root),
        },
    )

    run(
        [
            str(args.translator_python),
            str(args.translator_root / "generator/bpmn_to_dsl.py"),
            str(args.bpmn_file),
            "-o",
            str(dsl_file),
            "--name",
            args.case_name,
        ],
        cwd=args.translator_root,
    )
    run([sys.executable, str(SCRIPTS / "extract_bpmn_structure.py"), "--bpmn-file", str(args.bpmn_file), "--case-name", args.case_name, "--out-dir", str(bpmn_out)])
    run([sys.executable, str(SCRIPTS / "extract_dsl_structure.py"), "--dsl-file", str(dsl_file), "--case-name", args.case_name, "--out-dir", str(dsl_out)])
    run([
        sys.executable,
        str(SCRIPTS / "build_bpmn_dsl_trace.py"),
        "--bpmn-tag",
        str(bpmn_out / "bpmn_tag.json"),
        "--dsl-tag",
        str(dsl_out / "dsl_tag.json"),
        "--contract",
        str(contract_file),
        "--out-file",
        str(trace_out / "bpmn_dsl_trace.json"),
    ])
    result = run([
        sys.executable,
        str(SCRIPTS / "check_structure_consistency.py"),
        "--bpmn-tag",
        str(bpmn_out / "bpmn_tag.json"),
        "--dsl-tag",
        str(dsl_out / "dsl_tag.json"),
        "--trace",
        str(trace_out / "bpmn_dsl_trace.json"),
        "--report-dir",
        str(reports_out),
    ], allow_fail=True)

    print(f"\nCase output: {out}")
    print(f"Summary: {reports_out / 'structure_summary.md'}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
