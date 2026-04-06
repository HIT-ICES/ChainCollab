#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from common import dump_json, dump_text, load_json


def collect_case_summaries(results_dir: Path) -> List[Dict[str, Any]]:
    rows = []
    for case_dir in sorted((results_dir / "cases").glob("*")):
        go_report_path = case_dir / "dsl_go_report.json"
        sol_report_path = case_dir / "dsl_sol_report.json"
        dsl_ast_path = case_dir / "dsl_ast.json"
        if not (go_report_path.exists() and sol_report_path.exists() and dsl_ast_path.exists()):
            continue
        dsl_ast = load_json(dsl_ast_path)
        go_report = load_json(go_report_path)
        sol_report = load_json(sol_report_path)
        rows.append(
            {
                "case_name": case_dir.name,
                "dsl_globals": len(dsl_ast.get("globals", [])),
                "dsl_messages": len(dsl_ast.get("messages", [])),
                "dsl_flows": len(dsl_ast.get("flows", [])),
                "go_coverage": go_report["summary"]["dsl_element_coverage"],
                "solidity_coverage": sol_report["summary"]["dsl_element_coverage"],
                "notes": summarize_notes(go_report, sol_report),
            }
        )
    return rows


def summarize_notes(go_report: Dict[str, Any], sol_report: Dict[str, Any]) -> str:
    go_missing = next((item for item in go_report.get("elements", []) if not item.get("matched")), None)
    sol_missing = next((item for item in sol_report.get("elements", []) if not item.get("matched")), None)
    notes = []
    if go_missing:
        notes.append(f"Go gap: {go_missing['element_name']}")
    if sol_missing:
        notes.append(f"Sol gap: {sol_missing['element_name']}")
    return "; ".join(notes) if notes else "No major gaps in sampled rules."


def render_markdown(rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# Experiment 2 Semantic Verification Summary",
        "",
        "| Case | DSL Globals | DSL Messages | DSL Flows | Go Coverage | Solidity Coverage | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_name']} | {row['dsl_globals']} | {row['dsl_messages']} | {row['dsl_flows']} | "
            f"{row['go_coverage']:.2%} | {row['solidity_coverage']:.2%} | {row['notes']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Experiment 2 reports.")
    parser.add_argument("--results-dir", required=True, help="Results directory.")
    args = parser.parse_args()

    results_dir = Path(args.results_dir).resolve()
    rows = collect_case_summaries(results_dir)
    summary = {"cases": rows, "case_count": len(rows)}
    dump_json(results_dir / "exp2_summary.json", summary)
    dump_text(results_dir / "exp2_summary.md", render_markdown(rows))


if __name__ == "__main__":
    main()
