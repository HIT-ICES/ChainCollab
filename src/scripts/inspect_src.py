#!/usr/bin/env python3
import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ModuleSummary:
    name: str
    category: str
    size: str
    stacks: list[str]
    compose_files: int
    has_readme: bool
    notes: list[str]


CATEGORY_MAP = {
    "backend": "platform",
    "front": "platform",
    "agent": "platform",
    "deployment": "platform",
    "runtime": "platform",
    "oracle": "oracle-core",
    "newTranslator": "modeling",
    "bpmn-chor-app": "modeling",
    "jsoncodeeditor": "modeling",
    "oracle-node": "oracle-experimental",
    "oracle-data-compute-lab": "oracle-experimental",
    "crosschain-relay-lab": "relay-experimental",
    "relayer-node": "relay-experimental",
    "crosschain_adapter": "relay-experimental",
    "geth-node": "chain-runtime",
    "geth_identity_contract": "chain-runtime",
}

NOTE_MAP = {
    "crosschain-relay-lab": ["Potential canonical relay prototype"],
    "relayer-node": ["Legacy relay path; evaluate merge/remove"],
    "crosschain_adapter": ["Legacy adapter path; evaluate merge/remove"],
    "oracle": ["Canonical backend-integrated oracle scripts"],
    "oracle-node": ["Parallel oracle stack; verify ownership"],
    "oracle-data-compute-lab": ["Experiment-only folder"],
    "runtime": ["Generated logs/state; not source of truth"],
}


def dir_size_human(path: Path) -> str:
    try:
        result = subprocess.run(
            ["du", "-sh", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.split()[0]
    except FileNotFoundError:
        pass
    return "-"


def detect_stacks(path: Path) -> list[str]:
    stacks: list[str] = []
    if (path / "manage.py").exists():
        stacks.append("django")
    if (path / "package.json").exists():
        stacks.append("node")
    if (path / "go.mod").exists():
        stacks.append("go")
    if (path / "requirements.txt").exists():
        stacks.append("python")
    if list(path.glob("docker-compose*.yml")):
        stacks.append("compose")
    return stacks


def inspect_src() -> list[ModuleSummary]:
    modules: list[ModuleSummary] = []
    for entry in sorted(SRC_ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        compose_files = len(list(entry.glob("docker-compose*.yml")))
        module = ModuleSummary(
            name=entry.name,
            category=CATEGORY_MAP.get(entry.name, "unclassified"),
            size=dir_size_human(entry),
            stacks=detect_stacks(entry),
            compose_files=compose_files,
            has_readme=(entry / "README.md").exists(),
            notes=NOTE_MAP.get(entry.name, []),
        )
        modules.append(module)
    return modules


def render_table(modules: list[ModuleSummary]) -> str:
    headers = ["module", "category", "size", "stacks", "compose", "readme", "notes"]
    rows = []
    for item in modules:
        rows.append(
            [
                item.name,
                item.category,
                item.size,
                ",".join(item.stacks) if item.stacks else "-",
                str(item.compose_files),
                "yes" if item.has_readme else "no",
                " | ".join(item.notes) if item.notes else "-",
            ]
        )
    widths = [
        max(len(headers[i]), max((len(r[i]) for r in rows), default=0))
        for i in range(len(headers))
    ]
    line = "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    sep = "  ".join("-" * widths[i] for i in range(len(headers)))
    out = [line, sep]
    for row in rows:
        out.append("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect /src module layout.")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument(
        "--write",
        type=str,
        default="",
        help="Write JSON output to this file path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    modules = inspect_src()
    payload = [asdict(x) for x in modules]

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_table(modules))

    if args.write:
        out_path = Path(args.write).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
