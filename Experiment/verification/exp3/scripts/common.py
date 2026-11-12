from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
EXP3_ROOT = SCRIPT_DIR.parent
CHAINCOLLAB_ROOT = EXP3_ROOT.parents[2]
GRAMMAR_PATH = CHAINCOLLAB_ROOT / "src" / "newTranslator" / "DSL" / "B2CDSL" / "b2cdsl" / "b2c.tx"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload: Dict[str, Any] | List[Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def dump_text(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_name(value: str | None) -> str:
    raw = (value or "").strip()
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in raw).strip("_")


def python_path_setup() -> None:
    translator_root = CHAINCOLLAB_ROOT / "src" / "newTranslator"
    if str(translator_root) not in sys.path:
        sys.path.insert(0, str(translator_root))
