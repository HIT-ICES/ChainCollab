#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_element_id(step: dict[str, Any]) -> tuple[str, str]:
    trigger = step.get("trigger")
    if isinstance(trigger, dict) and trigger.get("element"):
        return str(trigger["element"]), "step.trigger.element"
    for field in ("element", "activity_id", "id", "target"):
        if step.get(field):
            return str(step[field]), f"step.{field}"
    return "", ""


def trace_index(trace: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for section in ("links", "relation_links"):
        for link in trace.get(section, []):
            if link.get("status") != "matched":
                continue
            target_id = link.get("target_id")
            if target_id:
                index.setdefault(str(target_id), []).append({**link, "trace_section": section})
    for item in trace.get("represented_sources", []):
        for target_id in item.get("represented_by", []) or []:
            index.setdefault(str(target_id), []).append(
                {
                    "source_id": item.get("source_id"),
                    "source_type": item.get("source_type"),
                    "target_id": target_id,
                    "target_type": "represented",
                    "rule_name": item.get("rule_name"),
                    "status": "matched",
                    "match_method": "represented_by",
                    "trace_section": "represented_sources",
                }
            )
    return index


def check_logical_path(path_file: Path, dsl_tag: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    logical_path = read_json(path_file)
    dsl_nodes = {node["id"]: node for node in dsl_tag.get("nodes", [])}
    traces = trace_index(trace)
    failures: list[dict[str, Any]] = []
    step_results: list[dict[str, Any]] = []

    steps = logical_path.get("steps", [])
    for index, step in enumerate(steps):
        element_id, source_field = extract_element_id(step)
        exists_in_dsl = bool(element_id and element_id in dsl_nodes)
        trace_links = traces.get(element_id, []) if element_id else []
        traceable = exists_in_dsl and bool(trace_links)
        result = {
            "step_index": index,
            "step_type": step.get("type"),
            "element_id": element_id,
            "element_field": source_field,
            "exists_in_dsl_tag": exists_in_dsl,
            "traceable_to_bpmn": traceable,
            "trace_links": trace_links,
        }
        if not element_id:
            failure = {
                "path_name": logical_path.get("path_name", path_file.parent.name),
                "logical_path_file": str(path_file),
                "step_index": index,
                "failure_type": "PathStepElementMissing",
                "reason": "No supported element field found in logical_path step.",
                "step": step,
            }
            failures.append(failure)
            result["failure"] = failure
        elif not exists_in_dsl:
            failure = {
                "path_name": logical_path.get("path_name", path_file.parent.name),
                "logical_path_file": str(path_file),
                "step_index": index,
                "element_id": element_id,
                "failure_type": "PathStepElementNotInDslTag",
                "reason": "logical_path step element does not exist in dsl_tag.nodes.",
            }
            failures.append(failure)
            result["failure"] = failure
        elif not trace_links:
            failure = {
                "path_name": logical_path.get("path_name", path_file.parent.name),
                "logical_path_file": str(path_file),
                "step_index": index,
                "element_id": element_id,
                "failure_type": "PathStepUntraceable",
                "reason": "logical_path step element exists in DSL but has no BPMN source in bpmn_dsl_trace.json.",
            }
            failures.append(failure)
            result["failure"] = failure
        step_results.append(result)

    total_steps = len(steps)
    traceable_steps = total_steps - len(failures)
    return {
        "path_name": logical_path.get("path_name", path_file.parent.name),
        "logical_path_file": str(path_file),
        "expect": logical_path.get("expect"),
        "total_steps": total_steps,
        "traceable_steps": traceable_steps,
        "untraceable_steps": failures,
        "path_traceability": traceable_steps / total_steps if total_steps else 1.0,
        "steps": step_results,
    }


def write_markdown(report: dict[str, Any], output_file: Path) -> None:
    lines = [
        "# 1B Addition Path Traceability Summary",
        "",
        f"Case: {report['case_name']}",
        f"Status: {report['exp3_path_traceability_status']}",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| logical_paths | {report['logical_paths']} |",
        f"| logical_path_steps | {report['logical_path_steps']} |",
        f"| traceable_logical_path_steps | {report['traceable_logical_path_steps']} |",
        f"| untraceable_logical_path_steps | {report['untraceable_logical_path_steps']} |",
        f"| path_traceability | {report['overall_path_traceability']:.4f} |",
        "",
        "| Path | Steps | Traceable | Traceability | Failures |",
        "|---|---:|---:|---:|---:|",
    ]
    for path in report["paths"]:
        lines.append(
            f"| {path['path_name']} | {path['total_steps']} | {path['traceable_steps']} | "
            f"{path['path_traceability']:.4f} | {len(path['untraceable_steps'])} |"
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--logical-paths-dir", type=Path, required=True)
    parser.add_argument("--dsl-tag", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    dsl_tag = read_json(args.dsl_tag)
    trace = read_json(args.trace)
    path_files = sorted(args.logical_paths_dir.glob("*/logical_path.json"))
    path_reports = [check_logical_path(path_file, dsl_tag, trace) for path_file in path_files]

    total_steps = sum(item["total_steps"] for item in path_reports)
    traceable_steps = sum(item["traceable_steps"] for item in path_reports)
    untraceable_steps = total_steps - traceable_steps
    overall = traceable_steps / total_steps if total_steps else 1.0
    status = "PASS" if overall == 1.0 and untraceable_steps == 0 else "FAIL"
    report = {
        "case_name": args.case_name,
        "exp3_path_traceability_status": status,
        "logical_paths_dir": str(args.logical_paths_dir),
        "dsl_tag": str(args.dsl_tag),
        "trace": str(args.trace),
        "logical_paths": len(path_reports),
        "logical_path_steps": total_steps,
        "traceable_logical_path_steps": traceable_steps,
        "untraceable_logical_path_steps": untraceable_steps,
        "overall_path_traceability": overall,
        "paths": path_reports,
    }
    write_json(args.out_dir / "path_traceability_report.json", report)
    write_markdown(report, args.out_dir / "path_traceability_summary.md")
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
