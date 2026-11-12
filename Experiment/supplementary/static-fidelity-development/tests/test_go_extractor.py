from pathlib import Path

from tools.common import load_json, run_command


def test_go_extractor(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "go_ir.json"
    run_command(
        ["python3", str(root / "tools" / "extract_go_ir.py"), "--input", str(root / "tests" / "fixtures" / "minimal.go"), "--output", str(out)],
        cwd=root,
        context="go extractor test",
    )
    payload = load_json(out)
    assert any(item["name"] == "Approved" for item in payload["globals"])
    assert any(handler["trigger"]["kind"] == "message_completed" for handler in payload["handlers"])

