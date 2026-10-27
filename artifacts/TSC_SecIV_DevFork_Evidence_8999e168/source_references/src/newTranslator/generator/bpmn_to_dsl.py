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
from generator.split_mode import SplitModeConfig, generate_split_mode_artifacts  # type: ignore


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
    parser.add_argument(
        "--split-mode",
        action="store_true",
        help=(
            "Enable split generation mode. If disabled (default), split markers are ignored."
        ),
    )
    parser.add_argument(
        "--split-point-id",
        action="append",
        default=[],
        help="Manually specify BPMN node id(s) as split markers (repeatable).",
    )
    parser.add_argument(
        "--merge-point-id",
        default="",
        help="Optional BPMN node id used as merge/end boundary for closed-interval extraction.",
    )
    parser.add_argument(
        "--split-marker-key",
        default="splitPoint",
        help="BPMN documentation JSON key used for split marker detection.",
    )
    parser.add_argument(
        "--split-output-dir",
        type=Path,
        default=Path("build/split"),
        help="Split mode output root directory.",
    )
    parser.add_argument(
        "--split-contracts-dir",
        type=Path,
        default=None,
        help=(
            "Optional output directory for split contracts; defaults to <split-output-dir>/<case>/split/contracts."
        ),
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

        if args.split_mode:
            split_cfg = SplitModeConfig(
                bpmn_path=args.bpmn_file.resolve(),
                b2c_output_path=output_path.resolve(),
                translator_root=Path(__file__).resolve().parent.parent,
                split_output_dir=args.split_output_dir.resolve(),
                split_contract_dir=args.split_contracts_dir.resolve()
                if args.split_contracts_dir
                else None,
                split_point_ids=args.split_point_id,
                merge_point_id=(args.merge_point_id.strip() or None),
                split_marker_key=args.split_marker_key,
                contract_name=args.contract_name,
            )
            result = generate_split_mode_artifacts(split_cfg)
            print(f"Split plan written to {result.get('planPath')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
