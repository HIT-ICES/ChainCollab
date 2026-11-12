#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from common import EXP3_ROOT, dump_json, dump_text, load_json


def discover_logical_paths(paths_dir: Path) -> List[Path]:
    candidates = sorted(paths_dir.glob("*/logical_path.json"))
    if not candidates:
        raise FileNotFoundError(f"No logical_path.json files found under {paths_dir}")
    return candidates


def infer_case_name(paths_dir: Path) -> str:
    parts = paths_dir.resolve().parts
    if "paths" in parts:
        index = parts.index("paths")
        if index > 0:
            return parts[index - 1]
    return paths_dir.resolve().parent.name


def path_name_for(logical_path: Path) -> str:
    return logical_path.parent.name


def latest_replay(output_dir: Path, started_at: float) -> Path | None:
    candidates = [
        path
        for path in output_dir.glob("replay_*.json")
        if path.stat().st_mtime >= started_at - 1
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.stat().st_mtime)[-1]


def fabric_replay_dir(case_name: str, path_name: str) -> Path:
    return EXP3_ROOT / "fabric" / case_name / "paths" / path_name / "replays"


def comparison_summary(case_name: str, path_name: str) -> Dict[str, Any]:
    base = EXP3_ROOT / "outputs" / case_name / "paths" / path_name
    result: Dict[str, Any] = {}
    for name in ("dsl_fabric", "solidity_fabric"):
        path = base / f"comparison.{name}.json"
        if not path.exists():
            result[name] = {"exists": False}
            continue
        payload = load_json(path)
        result[name] = {
            "exists": True,
            "path": str(path),
            "consistent": payload.get("consistent"),
            "finding_count": payload.get("finding_count"),
            "left_steps": (payload.get("left") or {}).get("step_count"),
            "right_steps": (payload.get("right") or {}).get("step_count"),
        }
    normalized = base / "normalized" / "fabric.normalized.json"
    result["fabric_normalized"] = str(normalized) if normalized.exists() else ""
    return result


def run_one(
    *,
    config: Path,
    logical_path: Path,
    case_name: str,
    no_compare: bool,
    extra_args: List[str],
) -> Dict[str, Any]:
    path_name = path_name_for(logical_path)
    output_dir = fabric_replay_dir(case_name, path_name)
    started_at = time.time()
    cmd = [
        sys.executable,
        str(EXP3_ROOT / "scripts" / "replay_fabric_instance.py"),
        "--config",
        str(config),
        "--sequence-file",
        str(logical_path),
        "--output-dir",
        str(output_dir),
    ]
    if no_compare:
        cmd.append("--no-compare")
    cmd.extend(extra_args)

    print(f"\n== Fabric replay {path_name} ==")
    print(" ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=str(EXP3_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)

    replay = latest_replay(output_dir, started_at) if completed.returncode == 0 else None
    item: Dict[str, Any] = {
        "path_name": path_name,
        "logical_path": str(logical_path),
        "output_dir": str(output_dir),
        "returncode": completed.returncode,
        "success": completed.returncode == 0,
        "replay_json": str(replay) if replay else "",
    }
    if completed.returncode == 0 and not no_compare:
        item["comparison"] = comparison_summary(case_name, path_name)
    return item


def render_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Fabric Case Paths Replay",
        "",
        f"- Case: `{summary.get('case_name')}`",
        f"- Paths dir: `{summary.get('paths_dir')}`",
        f"- Config: `{summary.get('config')}`",
        f"- Total: `{summary.get('total')}`",
        f"- Succeeded: `{summary.get('succeeded')}`",
        f"- Failed: `{summary.get('failed')}`",
        "",
        "## Paths",
        "",
    ]
    for item in summary.get("paths", []):
        status = "success" if item.get("success") else "failed"
        lines.append(f"- `{item.get('path_name')}`: `{status}`")
        if item.get("replay_json"):
            lines.append(f"  - replay: `{item.get('replay_json')}`")
        comparison = item.get("comparison") or {}
        for name in ("dsl_fabric", "solidity_fabric"):
            report = comparison.get(name) or {}
            if report.get("exists"):
                lines.append(
                    f"  - {name}: consistent=`{report.get('consistent')}`, "
                    f"findings=`{report.get('finding_count')}`, "
                    f"steps=`{report.get('left_steps')}/{report.get('right_steps')}`"
                )
        if not item.get("success"):
            lines.append(f"  - returncode: `{item.get('returncode')}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Fabric automatic replay for every logical path in an exp3 case paths directory.")
    parser.add_argument("--config", required=True, help="Fabric replay config JSON")
    parser.add_argument("--paths-dir", required=True, help="Case paths directory, e.g. cases/SupplyChainPaper/paths")
    parser.add_argument("--case-name", default="", help="Optional case name override")
    parser.add_argument("--only", nargs="*", default=[], help="Optional path directory names to run, e.g. SupplyChainPaper_auto_path_001")
    parser.add_argument("--summary-dir", default="", help="Directory for batch summary JSON/Markdown")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop after the first failed path")
    parser.add_argument("--no-compare", action="store_true", help="Pass --no-compare to replay_fabric_instance.py")
    parser.add_argument("--dry-run", action="store_true", help="Print discovered paths without running Fabric replay")
    parser.add_argument("--replay-arg", action="append", default=[], help="Extra argument forwarded to replay_fabric_instance.py; repeat as needed")
    args = parser.parse_args()

    config = Path(args.config).resolve()
    paths_dir = Path(args.paths_dir).resolve()
    case_name = args.case_name or infer_case_name(paths_dir)
    selected = set(args.only or [])
    logical_paths = discover_logical_paths(paths_dir)
    if selected:
        logical_paths = [path for path in logical_paths if path.parent.name in selected]
        missing = sorted(selected - {path.parent.name for path in logical_paths})
        if missing:
            raise SystemExit(f"Requested paths not found: {', '.join(missing)}")

    if args.dry_run:
        print(f"Case: {case_name}")
        for path in logical_paths:
            print(path)
        return 0

    results: List[Dict[str, Any]] = []
    for logical_path in logical_paths:
        item = run_one(
            config=config,
            logical_path=logical_path,
            case_name=case_name,
            no_compare=args.no_compare,
            extra_args=list(args.replay_arg or []),
        )
        results.append(item)
        if args.stop_on_failure and not item["success"]:
            break

    summary = {
        "case_name": case_name,
        "paths_dir": str(paths_dir),
        "config": str(config),
        "total": len(results),
        "succeeded": sum(1 for item in results if item.get("success")),
        "failed": sum(1 for item in results if not item.get("success")),
        "paths": results,
    }
    summary_dir = Path(args.summary_dir).resolve() if args.summary_dir else EXP3_ROOT / "fabric" / case_name / "batch"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = summary_dir / f"fabric_batch_{timestamp}.json"
    md_path = summary_dir / f"fabric_batch_{timestamp}.md"
    dump_json(json_path, summary)
    dump_text(md_path, render_markdown(summary))
    print(f"\nBatch summary JSON: {json_path}")
    print(f"Batch summary Markdown: {md_path}")
    print(f"Succeeded: {summary['succeeded']}/{summary['total']}; failed: {summary['failed']}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
