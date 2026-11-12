#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common import EXP2_ROOT, dump_json, dump_text, load_json


def _load_case_manifest(cases_dir: Path, case_name: str) -> Dict[str, Any]:
    manifest_path = cases_dir / case_name / "case.json"
    if not manifest_path.exists():
        return {}
    return load_json(manifest_path)


def _case_type(cases_dir: Path, case_name: str) -> str:
    manifest = _load_case_manifest(cases_dir, case_name)
    declared = (manifest.get("case_type") or manifest.get("polarity") or "").strip().lower()
    if declared in {"positive", "negative"}:
        return declared

    lowered = case_name.lower()
    if lowered.startswith(("negative_", "neg_", "invalid_", "mutant_", "mutation_", "random_negative_")):
        return "negative"
    return "positive"


def resolve_case_type(cases_dir: Path, case_name: str) -> str:
    return _case_type(cases_dir, case_name)


def _load_report(path: Path) -> Dict[str, Any]:
    data = load_json(path)
    data.setdefault("elements", [])
    return data


def summarize_case_assertions(case_assertions: Dict[str, Any]) -> str:
    assertions = case_assertions.get("assertions", [])
    if not assertions:
        return "N/A"

    observed = [item for item in assertions if item.get("status") != "unobserved"]
    satisfied = [item for item in observed if item.get("meets_expectation") is True]
    violated = [item for item in observed if item.get("meets_expectation") is False]
    unobserved = [item for item in assertions if item.get("status") == "unobserved"]

    if not observed:
        return "PASS"

    if violated:
        return f"FAIL ({len(violated)} assertion(s) failed)"
    return "PASS"


def collect_case_summaries(results_dir: Path, cases_dir: Path) -> List[Dict[str, Any]]:
    rows = []
    for case_dir in sorted((results_dir / "cases").glob("*")):
        go_report_path = case_dir / "go_semantic_report.json"
        sol_report_path = case_dir / "solidity_semantic_report.json"
        dsl_ast_path = case_dir / "dsl_ast.json"
        case_assertions_path = case_dir / "case_assertions.json"
        if not (go_report_path.exists() and sol_report_path.exists() and dsl_ast_path.exists()):
            continue
        dsl_ast = load_json(dsl_ast_path)
        go_report = _load_report(go_report_path)
        sol_report = _load_report(sol_report_path)
        case_assertions = load_json(case_assertions_path) if case_assertions_path.exists() else {"assertions": []}
        rows.append(
            {
                "case_name": case_dir.name,
                "case_type": _case_type(cases_dir, case_dir.name),
                "dsl_globals": len(dsl_ast.get("globals", [])),
                "dsl_messages": len(dsl_ast.get("messages", [])),
                "dsl_flows": len(dsl_ast.get("flows", [])),
                "go_coverage": go_report["summary"]["dsl_element_coverage"],
                "solidity_coverage": sol_report["summary"]["dsl_element_coverage"],
                "assertion_check": summarize_case_assertions(case_assertions),
                "notes": summarize_notes(go_report, sol_report),
            }
        )
    return rows


def summarize_notes(go_report: Dict[str, Any], sol_report: Dict[str, Any]) -> str:
    go_missing = next((item for item in go_report.get("elements", []) if not item.get("matched")), None)
    sol_missing = next((item for item in sol_report.get("elements", []) if not item.get("matched")), None)
    notes = []
    if go_missing:
        notes.append(f"Go gap: {go_missing['element_name']}")
    if sol_missing:
        notes.append(f"Sol gap: {sol_missing['element_name']}")
    return "; ".join(notes) if notes else "No major gaps in sampled rules."


def _load_assertions(assertion_table_path: Path) -> List[Dict[str, Any]]:
    payload = load_json(assertion_table_path)
    return payload.get("assertions", [])


def load_assertions(assertion_table_path: Path) -> List[Dict[str, Any]]:
    return _load_assertions(assertion_table_path)


def _build_report_index(results_dir: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    report_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for case_dir in sorted((results_dir / "cases").glob("*")):
        go_report_path = case_dir / "go_semantic_report.json"
        sol_report_path = case_dir / "solidity_semantic_report.json"
        if go_report_path.exists():
            report_index[(case_dir.name, "go")] = _load_report(go_report_path)
        if sol_report_path.exists():
            report_index[(case_dir.name, "solidity")] = _load_report(sol_report_path)
    return report_index


def _evaluate_target_assertion(report: Dict[str, Any], matcher: Dict[str, Any]) -> Dict[str, Any]:
    elements = report.get("elements", [])
    element_type = matcher.get("element_type")
    relevant = [item for item in elements if item.get("element_type") == element_type]
    if not relevant:
        return {"applicable": False, "passed": False, "reason": "no_relevant_elements"}

    all_matched = all(item.get("matched", False) for item in relevant)
    evidence_keywords = matcher.get("evidence_any", []) or []
    evidence_ok = True

    if evidence_keywords:
        evidence_ok = False
        for item in relevant:
            if not item.get("matched", False):
                continue
            blob = " ".join(item.get("evidence", []))
            if any(keyword in blob for keyword in evidence_keywords):
                evidence_ok = True
                break

    passed = all_matched and evidence_ok
    return {
        "applicable": True,
        "passed": passed,
        "total_relevant": len(relevant),
        "failed_relevant": sum(1 for item in relevant if not item.get("matched", False)),
        "evidence_guard": evidence_ok,
    }


def evaluate_case_assertions(
    case_name: str,
    case_type: str,
    reports_by_target: Dict[str, Dict[str, Any]],
    assertions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    case_results: List[Dict[str, Any]] = []

    for assertion in assertions:
        matcher = assertion.get("matcher", {})
        targets = assertion.get("targets", ["go", "solidity"])
        mode = assertion.get("mode", "positive")
        target_results: List[Dict[str, Any]] = []

        for target in targets:
            report = reports_by_target.get(target)
            if not report:
                continue
            result = _evaluate_target_assertion(report, matcher)
            if result["applicable"]:
                target_results.append({"target": target, **result})

        if not target_results:
            case_results.append(
                {
                    "id": assertion.get("id"),
                    "title": assertion.get("title"),
                    "dimension": assertion.get("dimension"),
                    "mode": mode,
                    "targets": targets,
                    "case_type": case_type,
                    "status": "unobserved",
                    "expected_outcome": None,
                    "validation_passed": False,
                    "meets_expectation": None,
                    "applicable_targets": [],
                    "details": [],
                }
            )
            continue

        validation_passed = all(item["passed"] for item in target_results)
        expected_outcome: Optional[str] = None
        status = "observed"
        meets_expectation: Optional[bool] = None

        if case_type == "negative" and mode in {"both", "negative"}:
            expected_outcome = "fail"
            meets_expectation = not validation_passed
            status = "triggered" if meets_expectation else "not_triggered"
        else:
            expected_outcome = "pass"
            meets_expectation = validation_passed
            status = "satisfied" if meets_expectation else "violated"

        case_results.append(
            {
                "id": assertion.get("id"),
                "title": assertion.get("title"),
                "dimension": assertion.get("dimension"),
                "mode": mode,
                "targets": targets,
                "case_type": case_type,
                "status": status,
                "expected_outcome": expected_outcome,
                "validation_passed": validation_passed,
                "meets_expectation": meets_expectation,
                "applicable_targets": [item["target"] for item in target_results],
                "details": target_results,
            }
        )

    return {
        "case_name": case_name,
        "case_type": case_type,
        "assertion_count": len(case_results),
        "assertions": case_results,
    }


def _status_for_assertion(mode: str, pos_total: int, pos_pass: int, neg_total: int, neg_fail: int) -> str:
    pos_ok = pos_total > 0 and pos_pass == pos_total
    neg_ok = neg_total > 0 and neg_fail > 0

    if mode == "positive":
        if pos_ok:
            return "covered"
        if pos_total == 0:
            return "unobserved"
        return "partial"

    if mode == "both":
        if pos_ok and neg_ok:
            return "covered"
        if pos_ok and neg_total == 0:
            return "positive_only"
        if pos_ok or neg_ok:
            return "partial"
        if pos_total == 0 and neg_total == 0:
            return "unobserved"
        return "uncovered"

    if mode == "negative":
        if neg_ok:
            return "covered"
        if neg_total == 0:
            return "unobserved"
        return "uncovered"

    return "unknown"


def compute_assertion_coverage(
    case_rows: List[Dict[str, Any]],
    report_index: Dict[Tuple[str, str], Dict[str, Any]],
    assertions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for assertion in assertions:
        matcher = assertion.get("matcher", {})
        targets = assertion.get("targets", ["go", "solidity"])
        mode = assertion.get("mode", "positive")

        positive_total = 0
        positive_passed = 0
        negative_total = 0
        negative_failed = 0
        positive_pass_cases: List[str] = []
        positive_fail_cases: List[str] = []
        negative_trigger_cases: List[str] = []

        for row in case_rows:
            case_name = row["case_name"]
            case_type = row.get("case_type", "positive")

            target_evals: List[Dict[str, Any]] = []
            for target in targets:
                report = report_index.get((case_name, target))
                if not report:
                    continue
                result = _evaluate_target_assertion(report, matcher)
                if result["applicable"]:
                    target_evals.append(result)

            if not target_evals:
                continue

            case_passed = all(item["passed"] for item in target_evals)

            if case_type == "negative":
                negative_total += 1
                if not case_passed:
                    negative_failed += 1
                    negative_trigger_cases.append(case_name)
            else:
                positive_total += 1
                if case_passed:
                    positive_passed += 1
                    positive_pass_cases.append(case_name)
                else:
                    positive_fail_cases.append(case_name)

        status = _status_for_assertion(mode, positive_total, positive_passed, negative_total, negative_failed)

        output.append(
            {
                "id": assertion.get("id"),
                "title": assertion.get("title"),
                "dimension": assertion.get("dimension"),
                "mode": mode,
                "targets": targets,
                "source": assertion.get("source", {}),
                "description": assertion.get("description", ""),
                "positive_cases_total": positive_total,
                "positive_cases_passed": positive_passed,
                "positive_coverage": (positive_passed / positive_total) if positive_total else None,
                "negative_cases_total": negative_total,
                "negative_cases_failed": negative_failed,
                "negative_trigger_rate": (negative_failed / negative_total) if negative_total else None,
                "status": status,
                "positive_pass_cases": positive_pass_cases,
                "positive_fail_cases": positive_fail_cases,
                "negative_trigger_cases": negative_trigger_cases,
            }
        )
    return output


def compute_assertion_coverage_from_case_assertions(
    case_assertion_payloads: List[Dict[str, Any]],
    assertions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for payload in case_assertion_payloads:
        case_name = payload.get("case_name")
        if not case_name:
            continue
        indexed[case_name] = payload

    output: List[Dict[str, Any]] = []
    for assertion in assertions:
        mode = assertion.get("mode", "positive")
        assertion_id = assertion.get("id")

        positive_total = 0
        positive_passed = 0
        negative_total = 0
        negative_failed = 0
        positive_pass_cases: List[str] = []
        positive_fail_cases: List[str] = []
        negative_trigger_cases: List[str] = []

        for case_name, payload in indexed.items():
            case_type = payload.get("case_type", "positive")
            case_assertion = next((item for item in payload.get("assertions", []) if item.get("id") == assertion_id), None)
            if not case_assertion or case_assertion.get("status") == "unobserved":
                continue

            if case_type == "negative":
                negative_total += 1
                if case_assertion.get("status") == "triggered":
                    negative_failed += 1
                    negative_trigger_cases.append(case_name)
            else:
                positive_total += 1
                if case_assertion.get("status") == "satisfied":
                    positive_passed += 1
                    positive_pass_cases.append(case_name)
                else:
                    positive_fail_cases.append(case_name)

        status = _status_for_assertion(mode, positive_total, positive_passed, negative_total, negative_failed)
        output.append(
            {
                "id": assertion.get("id"),
                "title": assertion.get("title"),
                "dimension": assertion.get("dimension"),
                "mode": mode,
                "targets": assertion.get("targets", ["go", "solidity"]),
                "source": assertion.get("source", {}),
                "description": assertion.get("description", ""),
                "positive_cases_total": positive_total,
                "positive_cases_passed": positive_passed,
                "positive_coverage": (positive_passed / positive_total) if positive_total else None,
                "negative_cases_total": negative_total,
                "negative_cases_failed": negative_failed,
                "negative_trigger_rate": (negative_failed / negative_total) if negative_total else None,
                "status": status,
                "positive_pass_cases": positive_pass_cases,
                "positive_fail_cases": positive_fail_cases,
                "negative_trigger_cases": negative_trigger_cases,
            }
        )
    return output


def _load_case_assertion_payloads(results_dir: Path) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    for case_dir in sorted((results_dir / "cases").glob("*")):
        path = case_dir / "case_assertions.json"
        if path.exists():
            payloads.append(load_json(path))
    return payloads


def render_assertion_markdown(assertion_rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# Assertion Coverage Summary",
        "",
        "| ID | Dimension | Mode | Targets | Positive | Negative Trigger | Status |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]

    for row in assertion_rows:
        pos = "N/A"
        if row["positive_coverage"] is not None:
            pos = f"{row['positive_coverage']:.2%} ({row['positive_cases_passed']}/{row['positive_cases_total']})"

        neg = "N/A"
        if row["negative_trigger_rate"] is not None:
            neg = f"{row['negative_trigger_rate']:.2%} ({row['negative_cases_failed']}/{row['negative_cases_total']})"

        lines.append(
            f"| {row['id']} | {row['dimension']} | {row['mode']} | {','.join(row['targets'])} | {pos} | {neg} | {row['status']} |"
        )

    lines.append("")
    lines.append("## Assertion Notes")
    lines.append("")
    for row in assertion_rows:
        lines.append(f"- {row['id']} {row['title']}")
        if row["positive_fail_cases"]:
            lines.append(f"  - positive failed: {', '.join(row['positive_fail_cases'])}")
        if row["negative_trigger_cases"]:
            lines.append(f"  - negative triggered: {', '.join(row['negative_trigger_cases'])}")
    return "\n".join(lines) + "\n"


def render_markdown(rows: List[Dict[str, Any]], assertion_rows: Optional[List[Dict[str, Any]]] = None) -> str:
    lines = [
        "# Experiment 2 Semantic Verification Summary",
        "",
        "| Case | Type | DSL Globals | DSL Messages | DSL Flows | Go Coverage | Solidity Coverage | Assertion Check | Notes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_name']} | {row['case_type']} | {row['dsl_globals']} | {row['dsl_messages']} | {row['dsl_flows']} | "
            f"{row['go_coverage']:.2%} | {row['solidity_coverage']:.2%} | {row['assertion_check']} | {row['notes']} |"
        )

    if assertion_rows:
        lines.extend(
            [
                "",
                "## Assertion Coverage",
                "",
                "| ID | Dimension | Mode | Targets | Positive | Negative Trigger | Status |",
                "| --- | --- | --- | --- | ---: | ---: | --- |",
            ]
        )
        for row in assertion_rows:
            pos = "N/A"
            if row["positive_coverage"] is not None:
                pos = f"{row['positive_coverage']:.2%} ({row['positive_cases_passed']}/{row['positive_cases_total']})"
            neg = "N/A"
            if row["negative_trigger_rate"] is not None:
                neg = f"{row['negative_trigger_rate']:.2%} ({row['negative_cases_failed']}/{row['negative_cases_total']})"
            lines.append(
                f"| {row['id']} | {row['dimension']} | {row['mode']} | {','.join(row['targets'])} | {pos} | {neg} | {row['status']} |"
            )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Experiment 2 reports.")
    parser.add_argument("--results-dir", required=True, help="Results directory.")
    parser.add_argument("--cases-dir", default=str(EXP2_ROOT / "cases"), help="Cases directory for case metadata.")
    parser.add_argument(
        "--assertion-table",
        default=str(EXP2_ROOT / "config" / "assertion_table.json"),
        help="Path to assertion_table.json",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir).resolve()
    cases_dir = Path(args.cases_dir).resolve()
    assertion_table_path = Path(args.assertion_table).resolve()

    rows = collect_case_summaries(results_dir, cases_dir)

    assertion_rows: List[Dict[str, Any]] = []
    if assertion_table_path.exists():
        assertions = _load_assertions(assertion_table_path)
        case_assertion_payloads = _load_case_assertion_payloads(results_dir)
        if case_assertion_payloads:
            assertion_rows = compute_assertion_coverage_from_case_assertions(case_assertion_payloads, assertions)
        else:
            report_index = _build_report_index(results_dir)
            assertion_rows = compute_assertion_coverage(rows, report_index, assertions)

    summary = {
        "cases": rows,
        "case_count": len(rows),
        "assertion_count": len(assertion_rows),
        "assertions": assertion_rows,
    }

    dump_json(results_dir / "exp2_summary.json", summary)
    dump_text(results_dir / "exp2_summary.md", render_markdown(rows, assertion_rows))

    if assertion_rows:
        dump_json(
            results_dir / "assertion_coverage.json",
            {
                "assertion_count": len(assertion_rows),
                "assertions": assertion_rows,
            },
        )
        dump_text(results_dir / "assertion_coverage.md", render_assertion_markdown(assertion_rows))


if __name__ == "__main__":
    main()
