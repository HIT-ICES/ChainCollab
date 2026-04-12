#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from tools.common import (
    EXP2_ROOT,
    NEW_TRANSLATOR_ROOT,
    dump_json,
    dump_text,
    ensure_parent,
    load_json,
    quote,
    resolve_case_name,
    run_command,
    run_nt,
)
from tools.compare_ir import compare, load_rules, report_markdown
from tools.extract_dsl_ir import parse_dsl


MAPPING_RULES = EXP2_ROOT / "config" / "mapping_rules.yaml"
ASSERTION_TABLE = EXP2_ROOT / "config" / "assertion_table.yaml"
CASE_ASSERTION_MATRIX = EXP2_ROOT / "config" / "case_assertion_matrix.yaml"
OUTPUTS_ROOT = EXP2_ROOT / "outputs"
POSITIVE_DIR = EXP2_ROOT / "cases" / "positive"
NEGATIVE_DIR = EXP2_ROOT / "cases" / "negative"


def load_assertion_context() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    table_raw = yaml.safe_load(ASSERTION_TABLE.read_text(encoding="utf-8")) or {}
    matrix_raw = yaml.safe_load(CASE_ASSERTION_MATRIX.read_text(encoding="utf-8")) or {}
    assertions = {item["id"]: item for item in table_raw.get("assertions", [])}
    matrix = {
        "positive_cases": matrix_raw.get("positive_cases", {}) or {},
        "negative_cases": matrix_raw.get("negative_cases", {}) or {},
    }
    return assertions, matrix


def discover_main_seed_groups() -> dict[str, list[Path]]:
    return {
        "positive": sorted(POSITIVE_DIR.glob("*.b2c")),
        "negative": sorted(NEGATIVE_DIR.glob("*.b2c")),
    }


def case_assertions(case_name: str, case_group: str, assertion_matrix: dict[str, dict[str, Any]]) -> list[str]:
    if case_group == "positive":
        return list((assertion_matrix.get("positive_cases", {}).get(case_name) or {}).get("covers", []))
    if case_group == "negative":
        return list((assertion_matrix.get("negative_cases", {}).get(case_name) or {}).get("targets", []))
    return []


def format_assertion_lines(assertion_ids: list[str], assertions: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for assertion_id in assertion_ids:
        item = assertions.get(assertion_id, {})
        title = item.get("title", "")
        source = item.get("source", {}) or {}
        source_rule = source.get("rule", "")
        source_file = source.get("file", "")
        details = []
        if source_rule:
            details.append(source_rule)
        if source_file:
            details.append(source_file)
        suffix = f" ({', '.join(details)})" if details else ""
        if title:
            lines.append(f"- `{assertion_id}`: {title}{suffix}")
        else:
            lines.append(f"- `{assertion_id}`{suffix}")
    return lines


def append_assertion_section(report: str, heading: str, assertion_ids: list[str], assertions: dict[str, dict[str, Any]]) -> str:
    lines = format_assertion_lines(assertion_ids, assertions)
    if not lines:
        return report
    return report + f"\n## {heading}\n\n" + "\n".join(lines) + "\n"


def generate_from_input(input_path: Path, case_name: str, target_dir: Path) -> dict[str, Path]:
    artifacts = {
        "dsl": target_dir / f"{case_name}.b2c",
        "go": target_dir / f"{case_name}.go",
        "sol": target_dir / f"{case_name}.sol",
    }
    ensure_parent(artifacts["dsl"])
    if input_path.suffix == ".b2c":
        artifacts["dsl"].write_text(input_path.read_text(encoding="utf-8"), encoding="utf-8")
    elif input_path.suffix == ".bpmn":
        run_nt(
            f"nt-bpmn-to-b2c {quote(input_path)} {quote(artifacts['dsl'])} -n {quote(case_name)}",
            context=f"generate DSL for {input_path.name}",
        )
    else:
        raise ValueError(f"Unsupported input suffix: {input_path.suffix}")

    run_nt("nt-go-clean", context="clean go build")
    run_nt(f"nt-go-gen {quote(artifacts['dsl'])}", context=f"generate go for {case_name}")
    source_go = sorted(
        path
        for path in (NEW_TRANSLATOR_ROOT / "build" / "chaincode").glob("*.go")
        if path.is_file() and path.name != "oracle_stub.go"
    )
    if not source_go:
        raise RuntimeError("Go generation did not produce any .go file.")
    artifacts["go"].write_text(source_go[0].read_text(encoding="utf-8"), encoding="utf-8")

    run_nt("nt-sol-clean", context="clean solidity build")
    run_nt(f"nt-sol-gen {quote(artifacts['dsl'])}", context=f"generate solidity for {case_name}")
    sol_files = sorted((NEW_TRANSLATOR_ROOT / "build" / "solidity").glob("*.sol"))
    if not sol_files:
        raise RuntimeError("Solidity generation did not produce any .sol file.")
    artifacts["sol"].write_text(sol_files[0].read_text(encoding="utf-8"), encoding="utf-8")
    return artifacts


def run_negative_case(
    input_path: Path,
    outdir: Path,
    *,
    case_name: str,
    assertions: dict[str, dict[str, Any]],
    assertion_matrix: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    copied_input = outdir / f"{case_name}{input_path.suffix}"
    copied_input.write_text(input_path.read_text(encoding="utf-8"), encoding="utf-8")
    targeted_assertions = case_assertions(case_name, "negative", assertion_matrix)

    try:
        parse_dsl(input_path)
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        dump_text(outdir / "dsl_parse_error.txt", error_text)
        dump_json(
            outdir / "negative_check.json",
            {
                "case_name": case_name,
                "expected_stage": "dsl_parse_or_reference_resolution",
                "result": "REJECTED_AS_EXPECTED",
                "targeted_assertions": targeted_assertions,
                "message": error_text,
            },
        )
        report = "\n".join(
            [
                f"# Negative Case Report: {case_name}",
                "",
                f"- 输入 DSL: `{copied_input}`",
                "- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败",
                "- 实际结果: 已按预期拒绝非法输入",
                "",
                "## 失败原因",
                "",
                f"- {error_text}",
                "",
                "## 结论",
                "",
                "- verdict: EXPECTED_REJECT",
                "",
            ]
        )
        report = append_assertion_section(report, "对应断言", targeted_assertions, assertions)
        dump_text(outdir / "report.md", report)
        return {
            "case_name": case_name,
            "case_group": "negative",
            "assertion_ids": targeted_assertions,
            "dsl": str(copied_input),
            "go": "",
            "sol": "",
            "go_verdict": "EXPECTED_REJECT",
            "sol_verdict": "EXPECTED_REJECT",
            "go_flow_coverage": 0.0,
            "sol_flow_coverage": 0.0,
            "solidity_available": False,
        }

    dump_json(
        outdir / "negative_check.json",
        {
            "case_name": case_name,
            "expected_stage": "dsl_parse_or_reference_resolution",
            "result": "UNEXPECTED_ACCEPT",
            "targeted_assertions": targeted_assertions,
        },
    )
    report = "\n".join(
        [
            f"# Negative Case Report: {case_name}",
            "",
            f"- 输入 DSL: `{copied_input}`",
            "- 预期结果: 在 DSL 解析 / 引用解析 / 约束阶段失败",
            "- 实际结果: 未被拒绝",
            "",
            "## 结论",
            "",
            "- verdict: UNEXPECTED_ACCEPT",
            "",
        ]
    )
    report = append_assertion_section(report, "对应断言", targeted_assertions, assertions)
    dump_text(outdir / "report.md", report)
    return {
        "case_name": case_name,
        "case_group": "negative",
        "assertion_ids": targeted_assertions,
        "dsl": str(copied_input),
        "go": "",
        "sol": "",
        "go_verdict": "UNEXPECTED_ACCEPT",
        "sol_verdict": "UNEXPECTED_ACCEPT",
        "go_flow_coverage": 0.0,
        "sol_flow_coverage": 0.0,
        "solidity_available": False,
    }


def run_case(
    input_path: Path,
    outdir: Path,
    *,
    case_name: str,
    assertions: dict[str, dict[str, Any]],
    assertion_matrix: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    case_group = input_path.parent.name if input_path.parent.name in {"positive", "negative"} else "custom"
    if case_group == "negative":
        return run_negative_case(
            input_path,
            outdir,
            case_name=case_name,
            assertions=assertions,
            assertion_matrix=assertion_matrix,
        )

    outdir.mkdir(parents=True, exist_ok=True)
    artifacts = generate_from_input(input_path, case_name, outdir)
    covered_assertions = case_assertions(case_name, "positive", assertion_matrix)

    dsl_ir = parse_dsl(artifacts["dsl"])
    dump_json(outdir / "dsl_ir.json", dsl_ir)

    run_command(
        ["python3", str(EXP2_ROOT / "tools" / "extract_go_ir.py"), "--input", str(artifacts["go"]), "--output", str(outdir / "go_ir.json")],
        cwd=EXP2_ROOT,
        context="extract go ir",
    )
    go_ir = load_json(outdir / "go_ir.json")

    sol_ir = None
    sol_error = None
    try:
        run_command(
            ["python3", str(EXP2_ROOT / "tools" / "extract_sol_ir.py"), "--input", str(artifacts["sol"]), "--output", str(outdir / "sol_ir.json")],
            cwd=EXP2_ROOT,
            context="extract solidity ir",
        )
        sol_ir = load_json(outdir / "sol_ir.json")
    except Exception as exc:  # noqa: BLE001
        sol_error = str(exc)
        dump_text(outdir / "sol_ir.error.txt", sol_error)

    rules = load_rules(MAPPING_RULES)
    go_compare = compare(dsl_ir, go_ir, rules, "go")
    dump_json(outdir / "compare_go.json", go_compare)

    sol_compare = None
    if sol_ir is not None:
        sol_compare = compare(dsl_ir, sol_ir, rules, "solidity")
        dump_json(outdir / "compare_sol.json", sol_compare)

    report = report_markdown(
        case_name,
        dsl_ir,
        go_compare,
        sol_compare,
        {"dsl": str(artifacts["dsl"]), "go": str(artifacts["go"]), "sol": str(artifacts["sol"])},
    )
    if sol_error:
        report += "\n## Solidity Extraction Note\n\n- " + sol_error + "\n"
    report = append_assertion_section(report, "覆盖断言", covered_assertions, assertions)
    dump_text(outdir / "report.md", report)
    return {
        "case_name": case_name,
        "case_group": case_group,
        "assertion_ids": covered_assertions,
        "dsl": str(artifacts["dsl"]),
        "go": str(artifacts["go"]),
        "sol": str(artifacts["sol"]),
        "go_verdict": go_compare["summary"]["verdict"],
        "sol_verdict": sol_compare["summary"]["verdict"] if sol_compare else "UNAVAILABLE",
        "go_flow_coverage": go_compare["summary"]["flow_coverage"],
        "sol_flow_coverage": sol_compare["summary"]["flow_coverage"] if sol_compare else 0.0,
        "solidity_available": sol_ir is not None,
    }


def write_summary(results: list[dict[str, Any]], output_root: Path) -> None:
    dump_json(output_root / "summary.json", {"cases": results})
    positive = [item for item in results if item.get("case_group") == "positive"]
    negative = [item for item in results if item.get("case_group") == "negative"]
    custom = [item for item in results if item.get("case_group") not in {"positive", "negative"}]
    lines = ["# Exp2 Summary", "", f"- 总案例数: {len(results)}", f"- 正例数: {len(positive)}", f"- 负例数: {len(negative)}", ""]
    if positive:
        lines.extend(["## 正例", ""])
        for item in positive:
            suffix = f", assertions={','.join(item.get('assertion_ids', []))}" if item.get("assertion_ids") else ""
            lines.append(f"- {item['case_name']}: go={item['go_verdict']} ({item['go_flow_coverage']}), solidity={item['sol_verdict']} ({item['sol_flow_coverage']}){suffix}")
        lines.append("")
    if negative:
        lines.extend(["## 负例", ""])
        for item in negative:
            suffix = f", assertions={','.join(item.get('assertion_ids', []))}" if item.get("assertion_ids") else ""
            lines.append(f"- {item['case_name']}: result={item['go_verdict']}{suffix}")
        lines.append("")
    if custom:
        lines.extend(["## 自定义输入", ""])
        for item in custom:
            lines.append(
                f"- {item['case_name']}: go={item['go_verdict']} ({item['go_flow_coverage']}), solidity={item['sol_verdict']} ({item['sol_flow_coverage']})"
            )
        lines.append("")
    dump_text(output_root / "summary.md", "\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run experiment 2 semantic fidelity validation.")
    parser.add_argument("--input", help="Input .b2c or .bpmn file.")
    parser.add_argument("--outdir", help="Output directory for a single case.")
    parser.add_argument("--case-name", help="Case name override.")
    parser.add_argument("--all-seeds", action="store_true", help="批量运行 cases/positive 与 cases/negative 下的全部样例。")
    args = parser.parse_args()

    assertions, assertion_matrix = load_assertion_context()
    results: list[dict[str, Any]] = []
    if args.all_seeds:
        for group_name, cases in discover_main_seed_groups().items():
            for seed in cases:
                case_name = resolve_case_name(seed)
                results.append(
                    run_case(
                        seed,
                        OUTPUTS_ROOT / group_name / case_name,
                        case_name=case_name,
                        assertions=assertions,
                        assertion_matrix=assertion_matrix,
                    )
                )
        write_summary(results, OUTPUTS_ROOT)
        return

    if not args.input:
        raise SystemExit("Either --input or --all-seeds is required.")
    input_path = Path(args.input).resolve()
    case_name = resolve_case_name(input_path, args.case_name)
    outdir = Path(args.outdir).resolve() if args.outdir else OUTPUTS_ROOT / case_name
    result = run_case(
        input_path,
        outdir,
        case_name=case_name,
        assertions=assertions,
        assertion_matrix=assertion_matrix,
    )
    write_summary([result], outdir.parent if args.outdir else OUTPUTS_ROOT)


if __name__ == "__main__":
    main()
