#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if not __package__:
    CURRENT_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = CURRENT_DIR.parent
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))

from generator.translator import GoChaincodeTranslator  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a BPMN diagram into the B2C DSL using GoChaincodeTranslator."
    )
    parser.add_argument(
        "bpmn_file",
        type=Path,
        help="Path to the BPMN (.bpmn) file to convert.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("build/chaincode/chaincode.b2c"),
        help="Destination path for the generated DSL file (default: build/chaincode/chaincode.b2c).",
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="contract_name",
        help="Optional contract name override. Defaults to the start event name if omitted.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the generated DSL to stdout instead of writing it to disk.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.bpmn_file.exists():
        print(f"Error: BPMN file '{args.bpmn_file}' does not exist.", file=sys.stderr)
        return 1

    translator = GoChaincodeTranslator(bpmn_file=str(args.bpmn_file))

    if args.print_only:
        dsl_text = translator.generate_chaincode(contract_name=args.contract_name)
        print(dsl_text)
    else:
        output_path = args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        translator.generate_chaincode(
            output_path=str(output_path),
            is_output=True,
            contract_name=args.contract_name,
        )
        print(f"DSL contract written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
