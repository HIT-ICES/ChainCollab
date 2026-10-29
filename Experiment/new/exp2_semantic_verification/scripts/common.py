from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
EXP2_ROOT = SCRIPT_DIR.parent
CHAINCOLLAB_ROOT = EXP2_ROOT.parents[2]
NEW_TRANSLATOR_ROOT = CHAINCOLLAB_ROOT / "src" / "newTranslator"
NEW_TRANSLATOR_PYTHON = NEW_TRANSLATOR_ROOT / ".venv" / "bin" / "python"
NT_SH = NEW_TRANSLATOR_ROOT / "nt.sh"
GRAMMAR_PATH = NEW_TRANSLATOR_ROOT / "DSL" / "B2CDSL" / "b2cdsl" / "b2c.tx"
GO_BUILD_DIR = NEW_TRANSLATOR_ROOT / "build" / "chaincode"
SOL_BUILD_DIR = NEW_TRANSLATOR_ROOT / "build" / "solidity"

if str(NEW_TRANSLATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(NEW_TRANSLATOR_ROOT))


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def dump_text(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_name(value: Optional[str]) -> str:
    raw = (value or "").strip()
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in raw).strip("_")


def quote_shell(path: Path | str) -> str:
    return shlex.quote(str(path))


def run_command(
    command: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        env=merged_env,
    )


def run_checked(
    command: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    context: str = "command",
) -> subprocess.CompletedProcess[str]:
    result = run_command(command, cwd=cwd, env=env)
    if result.returncode != 0:
        raise RuntimeError(
            f"{context} failed with exit code {result.returncode}\n"
            f"COMMAND: {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    return result


def run_nt_command(command_text: str, *, context: str) -> None:
    bash_command = f"source {quote_shell(NT_SH)} && {command_text}"
    run_checked(["/bin/bash", "-lc", bash_command], cwd=NEW_TRANSLATOR_ROOT, context=context)


def copy_if_exists(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Expected artifact not found: {source}")
    ensure_parent(target)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def discover_case_dirs(cases_dir: Path) -> List[Path]:
    discovered: List[Path] = []
    for path in sorted(cases_dir.iterdir()):
        if not path.is_dir():
            continue
        manifest_path = path / "case.json"
        manifest: Dict[str, Any] = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("enabled", True) is False:
                continue
        has_bpmn = (path / "input.bpmn").exists()
        has_b2c = (path / "input.b2c").exists()
        has_manifest_b2c = bool(manifest.get("source_b2c"))
        if not (has_bpmn or has_b2c or has_manifest_b2c):
            continue
        discovered.append(path)
    return discovered


def resolve_case(case_dir: Path) -> Dict[str, Any]:
    manifest_path = case_dir / "case.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "case_dir": case_dir,
        "case_name": manifest.get("case_name") or case_dir.name,
        "description": manifest.get("description", ""),
        "bpmn": case_dir / "input.bpmn" if (case_dir / "input.bpmn").exists() else None,
        "b2c": case_dir / "input.b2c" if (case_dir / "input.b2c").exists() else None,
        "source_b2c": Path(manifest["source_b2c"]).resolve() if manifest.get("source_b2c") else None,
        "dmn": case_dir / "input.dmn" if (case_dir / "input.dmn").exists() else None,
    }


def stage_b2c(case_info: Dict[str, Any], output_path: Path) -> Path:
    source = case_info.get("source_b2c") or case_info.get("b2c")
    if not source:
        raise ValueError(f"No DSL source configured for case {case_info['case_name']}")
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Configured DSL source not found: {source_path}")
    ensure_parent(output_path)
    shutil.copyfile(source_path, output_path)
    return output_path


def generate_b2c(bpmn_path: Path, output_path: Path, contract_name: str) -> Path:
    ensure_parent(output_path)
    run_nt_command(
        f"nt-bpmn-to-b2c {quote_shell(bpmn_path)} {quote_shell(output_path)} -n {shlex.quote(contract_name)}",
        context=f"BPMN -> B2C generation for {bpmn_path.name}",
    )
    return output_path


def generate_go(b2c_path: Path, output_path: Path) -> Path:
    run_nt_command("nt-go-clean", context="clean Go build directory")
    run_nt_command(f"nt-go-gen {quote_shell(b2c_path)}", context=f"B2C -> Go generation for {b2c_path.name}")
    root_sources = sorted(
        path
        for path in GO_BUILD_DIR.glob("*.go")
        if path.is_file() and path.name != "oracle_stub.go"
    )
    if not root_sources:
        raise FileNotFoundError(f"No Go source found in {GO_BUILD_DIR}")
    copy_if_exists(root_sources[0], output_path)
    return output_path


def generate_solidity(b2c_path: Path, output_path: Path) -> Path:
    run_nt_command("nt-sol-clean", context="clean Solidity build directory")
    run_nt_command(f"nt-sol-gen {quote_shell(b2c_path)}", context=f"B2C -> Solidity generation for {b2c_path.name}")
    root_sources = sorted(path for path in SOL_BUILD_DIR.glob("*.sol") if path.is_file())
    if not root_sources:
        raise FileNotFoundError(f"No Solidity source found in {SOL_BUILD_DIR}")
    copy_if_exists(root_sources[0], output_path)
    return output_path


def python_script() -> str:
    return str(NEW_TRANSLATOR_PYTHON if NEW_TRANSLATOR_PYTHON.exists() else Path(sys.executable))


def post_json(url: str, payload: Dict[str, Any], *, context: str) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{context} failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{context} failed: {exc}") from exc


def generate_b2c_via_api(bpmn_path: Path, output_path: Path, contract_name: str, api_base_url: str) -> Path:
    ensure_parent(output_path)
    payload = {
        "bpmnContent": bpmn_path.read_text(encoding="utf-8"),
        "artifactName": contract_name,
        "persist_to_runtime": False,
    }
    response = post_json(f"{api_base_url.rstrip('/')}/api/v1/chaincode/generate", payload, context=f"API BPMN -> B2C for {bpmn_path.name}")
    dsl_content = response.get("bpmnContent", "")
    if not dsl_content:
        raise RuntimeError("API BPMN -> B2C returned empty DSL content.")
    output_path.write_text(dsl_content, encoding="utf-8")
    return output_path


def compile_dsl_via_api(b2c_path: Path, output_path: Path, target: str, api_base_url: str) -> Path:
    ensure_parent(output_path)
    payload = {
        "dslContent": b2c_path.read_text(encoding="utf-8"),
        "target": target,
    }
    response = post_json(f"{api_base_url.rstrip('/')}/api/v1/chaincode/compile", payload, context=f"API DSL -> {target} for {b2c_path.name}")
    content = response.get("chaincodeContent", "")
    if not content:
        raise RuntimeError(f"API DSL -> {target} returned empty code content.")
    output_path.write_text(content, encoding="utf-8")
    return output_path
