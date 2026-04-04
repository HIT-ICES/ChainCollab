#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_json, parse_b2c_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse B2C DSL into unified JSON for exp1 mapping verification.")
    parser.add_argument("--b2c", required=True, help="Path to .b2c file.")
    parser.add_argument("--case-name", help="Override case name.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    args = parser.parse_args()

    payload = parse_b2c_file(Path(args.b2c).resolve(), case_name=args.case_name)
    dump_json(Path(args.output).resolve(), payload)


if __name__ == "__main__":
    main()
