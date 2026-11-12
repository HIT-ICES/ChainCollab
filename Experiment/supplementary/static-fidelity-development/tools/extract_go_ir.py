#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from tools.common import EXP2_ROOT, dump_json, load_json, run_command
from tools.normalize_ir import normalize_go_ir


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract normalized Go IR via the official Go AST.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    raw_path = output_path.with_name(output_path.stem + ".raw.json")
    extractor = EXP2_ROOT / "tools" / "extract_go_ir.go"

    run_command(
        ["go", "run", str(extractor), "--input", str(input_path), "--output", str(raw_path)],
        cwd=EXP2_ROOT,
        context="go ast extraction",
    )
    dump_json(output_path, normalize_go_ir(load_json(raw_path), input_path))


if __name__ == "__main__":
    main()

