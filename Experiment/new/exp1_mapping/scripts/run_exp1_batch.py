#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    discover_case_dirs,
    dump_json,
    dump_text,
    generate_b2c_with_newtranslator,
    parse_b2c_file,
    parse_bpmn_file,
    render_mapping_report_md,
    render_summary_md,
    resolve_case_files,
    verify_mapping,
    write_summary_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run exp1 BPMN -> B2CDSL mapping verification in batch mode.")
    parser.add_argument("--cases-dir", default=str(Path(__file__).resolve().parent.parent / "cases"), help="Cases directory.")
    parser.add_argument("--outputs-dir", default=str(Path(__file__).resolve().parent.parent / "outputs"), help="Outputs directory.")
    args = parser.parse_args()

    cases_dir = Path(args.cases_dir).resolve()
    outputs_dir = Path(args.outputs_dir).resolve()
    parsed_dir = outputs_dir / "parsed"
    reports_dir = outputs_dir / "reports"
    regenerated_dir = outputs_dir / "regenerated"
    summaries_dir = outputs_dir / "summaries"
    rows = []

    for case_dir in discover_case_dirs(cases_dir):
        files = resolve_case_files(case_dir)
        case_name = files["case_name"]
        if not files.get("bpmn"):
            continue

        generated_b2c = generate_b2c_with_newtranslator(
            files["bpmn"],
            regenerated_dir / f"{case_name}.generated.b2c",
            contract_name=case_name,
        )
        bpmn_json = parse_bpmn_file(files["bpmn"], files.get("dmn"), case_name=case_name)
        dsl_json = parse_b2c_file(generated_b2c, case_name=case_name)
        report = verify_mapping(bpmn_json, dsl_json)

        dump_json(parsed_dir / f"{case_name}.bpmn.json", bpmn_json)
        dump_json(parsed_dir / f"{case_name}.b2c.json", dsl_json)
        dump_json(reports_dir / f"{case_name}.mapping_report.json", report)
        dump_text(reports_dir / f"{case_name}.mapping_report.md", render_mapping_report_md(report))

        rows.append(
            {
                "Case": case_name,
                "Participants": len(bpmn_json.get("participants", [])),
                "Messages": len(bpmn_json.get("messages", [])),
                "Gateways": len(bpmn_json.get("gateways", [])),
                "Events": len(bpmn_json.get("events", [])),
                "BusinessRules": len(bpmn_json.get("businessrules", [])),
                "Contract Satisfaction": f"{report['contract_satisfaction_rate']:.2%}",
                "Element Preservation Rate": f"{report['element_preservation_rate']:.2%}",
                "Mapping Accuracy": f"{report['mapping_accuracy']:.2%}",
                "Pass/Fail": "PASS" if report["pass"] else "FAIL",
            }
        )

    write_summary_csv(summaries_dir / "summary.csv", rows)
    dump_text(summaries_dir / "summary.md", render_summary_md(rows))


if __name__ == "__main__":
    main()
