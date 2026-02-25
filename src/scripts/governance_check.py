#!/usr/bin/env python3
import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = SRC_ROOT / "docs" / "src-module-manifest.json"

ACTIVE_STATUSES = {"active"}


@dataclass
class Report:
    managed_count: int
    present_count: int
    missing_from_manifest: list[str]
    missing_on_disk: list[str]
    active_domain_conflicts: dict[str, list[str]]
    status_counts: dict[str, int]


def load_manifest(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("modules", [])


def list_src_dirs(src_root: Path) -> list[str]:
    names: list[str] = []
    for entry in sorted(src_root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        names.append(entry.name)
    return names


def build_report(modules: list[dict], present_dirs: list[str]) -> Report:
    module_names = [m["name"] for m in modules]
    status_counts: dict[str, int] = defaultdict(int)
    active_domain_map: dict[str, list[str]] = defaultdict(list)

    for module in modules:
        status = str(module.get("status", "unknown"))
        status_counts[status] += 1
        if status in ACTIVE_STATUSES:
            domain = str(module.get("domain", ""))
            if domain:
                active_domain_map[domain].append(module["name"])

    conflicts = {
        domain: names for domain, names in active_domain_map.items() if len(names) > 1
    }

    missing_from_manifest = sorted(set(present_dirs) - set(module_names))
    missing_on_disk = sorted(set(module_names) - set(present_dirs))

    return Report(
        managed_count=len(module_names),
        present_count=len(present_dirs),
        missing_from_manifest=missing_from_manifest,
        missing_on_disk=missing_on_disk,
        active_domain_conflicts=conflicts,
        status_counts=dict(sorted(status_counts.items())),
    )


def render(report: Report) -> str:
    lines = []
    lines.append("Src Governance Check")
    lines.append("====================")
    lines.append(f"Managed modules : {report.managed_count}")
    lines.append(f"Present folders : {report.present_count}")
    lines.append("")
    lines.append("Status counts")
    for status, count in report.status_counts.items():
        lines.append(f"- {status}: {count}")
    lines.append("")

    lines.append("Missing from manifest")
    if report.missing_from_manifest:
        lines.extend([f"- {name}" for name in report.missing_from_manifest])
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("Missing on disk")
    if report.missing_on_disk:
        lines.extend([f"- {name}" for name in report.missing_on_disk])
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("Active domain conflicts")
    if report.active_domain_conflicts:
        for domain, names in sorted(report.active_domain_conflicts.items()):
            lines.append(f"- {domain}: {', '.join(sorted(names))}")
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check /src governance manifest consistency.")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--manifest",
        default=str(MANIFEST),
        help="Manifest file path (default: src/docs/src-module-manifest.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        return 2

    modules = load_manifest(manifest_path)
    present_dirs = list_src_dirs(SRC_ROOT)
    report = build_report(modules, present_dirs)

    if args.json:
        print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))
    else:
        print(render(report))

    # Non-zero only for governance drift that should be actioned.
    if report.missing_from_manifest or report.active_domain_conflicts:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
