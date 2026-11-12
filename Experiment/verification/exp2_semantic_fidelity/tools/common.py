from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
EXP2_ROOT = TOOLS_DIR.parent
CHAINCOLLAB_ROOT = EXP2_ROOT.parents[2]
NEW_TRANSLATOR_ROOT = CHAINCOLLAB_ROOT / "src" / "newTranslator"
GRAMMAR_PATH = NEW_TRANSLATOR_ROOT / "DSL" / "B2CDSL" / "b2cdsl" / "b2c.tx"
NT_SH = NEW_TRANSLATOR_ROOT / "nt.sh"
PYTHON_BIN = Path(sys.executable)


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_text(path: Path, text: str) -> None:
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
    context: str = "command",
) -> CommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        text=True,
        input=input_text,
        capture_output=True,
    )
    result = CommandResult(args=args, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"{context} failed with exit code {proc.returncode}\n"
            f"COMMAND: {' '.join(args)}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}"
        )
    return result


def quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def run_nt(command: str, *, context: str) -> CommandResult:
    shell_command = f"source {quote(NT_SH)} && {command}"
    return run_command(["bash", "-lc", shell_command], cwd=NEW_TRANSLATOR_ROOT, context=context)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value.strip())
    return cleaned.strip("._") or "case"


def discover_seed_cases(seed_dir: Path) -> list[Path]:
    supported = []
    for pattern in ("*.b2c", "*.bpmn"):
        supported.extend(path for path in seed_dir.glob(pattern) if path.is_file())
    return sorted(supported)


def discover_case_groups(cases_root: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for group_name in ("positive", "negative"):
        group_dir = cases_root / group_name
        if not group_dir.exists():
            groups[group_name] = []
            continue
        groups[group_name] = discover_seed_cases(group_dir)
    return groups


def resolve_case_name(input_path: Path, explicit: str | None = None) -> str:
    if explicit:
        return safe_name(explicit)
    return safe_name(input_path.stem)
