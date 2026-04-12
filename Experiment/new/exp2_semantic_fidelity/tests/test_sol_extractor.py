import shutil
from pathlib import Path

import pytest

from tools.common import load_json, run_command


@pytest.mark.skipif(shutil.which("solc") is None, reason="solc not installed")
def test_sol_extractor(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "sol_ir.json"
    run_command(
        ["python3", str(root / "tools" / "extract_sol_ir.py"), "--input", str(root / "tests" / "fixtures" / "minimal.sol"), "--output", str(out)],
        cwd=root,
        context="sol extractor test",
    )
    payload = load_json(out)
    assert any(item["name"] == "Approved" for item in payload["globals"])
    assert any(handler["trigger"]["kind"] == "message_sent" for handler in payload["handlers"])

