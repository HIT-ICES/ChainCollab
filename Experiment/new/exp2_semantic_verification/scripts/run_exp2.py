#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from common import (
    EXP2_ROOT,
    compile_dsl_via_api,
    discover_case_dirs,
    dump_json,
    dump_text,
    generate_b2c,
    generate_b2c_via_api,
    generate_go,
    generate_solidity,
    python_script,
    resolve_case,
    run_checked,
    stage_b2c,
)
from summary_report import evaluate_case_assertions, load_assertions, resolve_case_type


def run_python(script: Path, args: List[str]) -> None:
    run_checked([python_script(), str(script)] + args, cwd=EXP2_ROOT, context=script.name)


def run_go_extractor(script: Path, input_path: Path, output_path: Path) -> None:
    run_checked(
        ["go", "run", str(script), "--input", str(input_path), "--output", str(output_path)],
        cwd=EXP2_ROOT,
        context="extract_go_ast.go",
    )


def run_node(script: Path, args: List[str]) -> None:
    run_checked(["node", str(script)] + args, cwd=EXP2_ROOT, context=script.name)


def run_solc_ast(solidity_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    input_payload = {
        "language": "Solidity",
        "sources": {
            solidity_path.name: {
                "content": solidity_path.read_text(encoding="utf-8"),
            }
        },
        "settings": {
            "outputSelection": {
                "*": {
                    "": ["ast"],
                }
            }
        },
    }
    input_path = output_path.with_name("solc_ast_input.json")
    input_path.write_text(json.dumps(input_payload), encoding="utf-8")
    run_checked(
        ["/bin/bash", "-lc", f"solc --standard-json < '{input_path}' > '{output_path}'"],
        cwd=EXP2_ROOT,
        context="solc standard-json AST export",
    )


def process_case(
    case_info: Dict[str, Any],
    results_dir: Path,
    *,
    backend: str,
    api_base_url: str | None,
    case_type: str,
    assertions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    scripts_dir = EXP2_ROOT / "scripts"
    case_dir = results_dir / "cases" / case_info["case_name"]
    case_dir.mkdir(parents=True, exist_ok=True)
    error_log_path = case_dir / "error.log"
    if error_log_path.exists():
        error_log_path.unlink()

    b2c_path = case_dir / "dsl.b2c"
    go_path = case_dir / "chaincode.go"
    sol_path = case_dir / "contract.sol"
    dsl_ast_path = case_dir / "dsl_ast.json"
    go_ast_path = case_dir / "go_ast.json"
    sol_ast_path = case_dir / "solidity_ast.json"
    sol_raw_ast_path = case_dir / "solc_ast_raw.json"
    go_report_path = case_dir / "go_semantic_report.json"
    sol_report_path = case_dir / "solidity_semantic_report.json"
    case_assertions_path = case_dir / "case_assertions.json"

    if case_info.get("source_b2c") or case_info.get("b2c"):
        stage_b2c(case_info, b2c_path)
    else:
        if backend == "api":
            if not api_base_url:
                raise ValueError("API backend requires --api-base-url.")
            if not case_info.get("bpmn"):
                raise ValueError(f"Case {case_info['case_name']} has no BPMN input for API generation.")
            generate_b2c_via_api(case_info["bpmn"], b2c_path, contract_name=case_info["case_name"], api_base_url=api_base_url)
        else:
            if not case_info.get("bpmn"):
                raise ValueError(f"Case {case_info['case_name']} has no BPMN input for CLI generation.")
            generate_b2c(case_info["bpmn"], b2c_path, contract_name=case_info["case_name"])

    if backend == "api":
        if not api_base_url:
            raise ValueError("API backend requires --api-base-url.")
        compile_dsl_via_api(b2c_path, go_path, "go", api_base_url)
        compile_dsl_via_api(b2c_path, sol_path, "solidity", api_base_url)
    else:
        generate_go(b2c_path, go_path)
        generate_solidity(b2c_path, sol_path)

    run_python(scripts_dir / "parse_b2c.py", ["--input", str(b2c_path), "--output", str(dsl_ast_path)])
    run_go_extractor(scripts_dir / "extract_go_ast.go", go_path, go_ast_path)
    run_solc_ast(sol_path, sol_raw_ast_path)
    run_node(scripts_dir / "extract_sol_ast.js", ["--ast-json", str(sol_raw_ast_path), "--output", str(sol_ast_path)])
    run_python(
        scripts_dir / "verify_dsl_go_semantics.py",
        ["--dsl-ast", str(dsl_ast_path), "--go-ast", str(go_ast_path), "--output", str(go_report_path), "--case-name", case_info["case_name"]],
    )
    run_python(
        scripts_dir / "verify_dsl_sol_semantics.py",
        ["--dsl-ast", str(dsl_ast_path), "--sol-ast", str(sol_ast_path), "--output", str(sol_report_path), "--case-name", case_info["case_name"]],
    )

    case_assertions = evaluate_case_assertions(
        case_info["case_name"],
        case_type,
        {
            "go": json.loads(go_report_path.read_text(encoding="utf-8")),
            "solidity": json.loads(sol_report_path.read_text(encoding="utf-8")),
        },
        assertions,
    )
    dump_json(case_assertions_path, case_assertions)

    return {
        "case_name": case_info["case_name"],
        "status": "ok",
        "artifacts": {
            "b2c": str(b2c_path),
            "go": str(go_path),
            "sol": str(sol_path),
            "dsl_ast": str(dsl_ast_path),
            "go_ast": str(go_ast_path),
            "sol_ast": str(sol_ast_path),
            "dsl_go_report": str(go_report_path),
            "dsl_sol_report": str(sol_report_path),
            "case_assertions": str(case_assertions_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Experiment 2 semantic verification in batch.")
    parser.add_argument("--cases-dir", default=str(EXP2_ROOT / "cases"), help="Directory containing case subdirectories.")
    parser.add_argument("--results-dir", default=str(EXP2_ROOT / "results"), help="Directory for generated reports.")
    parser.add_argument("--backend", choices=["cli", "api"], default="cli", help="Reuse newTranslator CLI wrappers or FastAPI endpoints.")
    parser.add_argument("--api-base-url", help="Base URL for newTranslator FastAPI service, for example http://127.0.0.1:8000")
    parser.add_argument(
        "--assertion-table",
        default=str(EXP2_ROOT / "config" / "assertion_table.json"),
        help="Path to assertion_table.json",
    )
    args = parser.parse_args()

    cases_dir = Path(args.cases_dir).resolve()
    results_dir = Path(args.results_dir).resolve()
    assertion_table_path = Path(args.assertion_table).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    assertions = load_assertions(assertion_table_path) if assertion_table_path.exists() else []

    run_log: List[Dict[str, Any]] = []
    for case_root in discover_case_dirs(cases_dir):
        case_info = resolve_case(case_root)
        case_type = resolve_case_type(cases_dir, case_info["case_name"])
        try:
            run_log.append(
                process_case(
                    case_info,
                    results_dir,
                    backend=args.backend,
                    api_base_url=args.api_base_url,
                    case_type=case_type,
                    assertions=assertions,
                )
            )
        except Exception as exc:  # noqa: BLE001
            failure = {
                "case_name": case_info["case_name"],
                "status": "failed",
                "error": str(exc),
            }
            run_log.append(failure)
            dump_text(results_dir / "cases" / case_info["case_name"] / "error.log", str(exc))

    dump_json(results_dir / "run_log.json", {"cases": run_log})
    run_python(
        EXP2_ROOT / "scripts" / "summary_report.py",
        ["--results-dir", str(results_dir), "--cases-dir", str(cases_dir), "--assertion-table", str(assertion_table_path)],
    )


if __name__ == "__main__":
    main()
