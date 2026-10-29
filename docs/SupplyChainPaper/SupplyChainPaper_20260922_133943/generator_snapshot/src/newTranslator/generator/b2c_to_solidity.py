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

from generator.translator import _load_b2c_metamodel, _render_solidity_contract  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a B2C DSL file into a Solidity contract using the local renderer."
    )
    parser.add_argument(
        "b2c_file",
        type=Path,
        help="Path to the B2C DSL (.b2c) file to compile.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("build/solidity/dsl.sol"),
        help="Destination Solidity file path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.b2c_file.exists():
        print(f"Error: B2C file '{args.b2c_file}' does not exist.", file=sys.stderr)
        return 1

    metamodel = _load_b2c_metamodel()
    model = metamodel.model_from_file(str(args.b2c_file))
    if not getattr(model, "contracts", None):
        print("Error: No contracts defined in DSL.", file=sys.stderr)
        return 1

    contract_content = _render_solidity_contract(args.b2c_file.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(contract_content, encoding="utf-8")
    print(f"Solidity contract written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
