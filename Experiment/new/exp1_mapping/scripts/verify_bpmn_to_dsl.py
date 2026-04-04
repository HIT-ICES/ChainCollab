#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_json, dump_text, load_json, render_mapping_report_md, verify_mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify BPMN -> B2CDSL mapping contracts.")
    parser.add_argument("--bpmn-json", required=True, help="Parsed BPMN JSON path.")
    parser.add_argument("--dsl-json", required=True, help="Parsed DSL JSON path.")
    parser.add_argument("--report-json", required=True, help="Output report JSON path.")
    parser.add_argument("--report-md", required=True, help="Output report Markdown path.")
    args = parser.parse_args()

    bpmn_data = load_json(Path(args.bpmn_json).resolve())
    dsl_data = load_json(Path(args.dsl_json).resolve())
    report = verify_mapping(bpmn_data, dsl_data)
    dump_json(Path(args.report_json).resolve(), report)
    dump_text(Path(args.report_md).resolve(), render_mapping_report_md(report))


if __name__ == "__main__":
    main()
