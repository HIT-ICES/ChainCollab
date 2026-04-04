#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_json, parse_bpmn_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse BPMN/DMN into unified JSON for exp1 mapping verification.")
    parser.add_argument("--bpmn", required=True, help="Path to BPMN file.")
    parser.add_argument("--dmn", help="Optional path to DMN file.")
    parser.add_argument("--case-name", help="Override case name.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    args = parser.parse_args()

    payload = parse_bpmn_file(
        Path(args.bpmn).resolve(),
        Path(args.dmn).resolve() if args.dmn else None,
        case_name=args.case_name,
    )
    dump_json(Path(args.output).resolve(), payload)


if __name__ == "__main__":
    main()
