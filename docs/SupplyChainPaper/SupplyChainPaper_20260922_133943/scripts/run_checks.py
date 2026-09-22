#!/usr/bin/env python3
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
LOGS = OUT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)


def run(name: str, argv: list[str], cwd: Path, extra_env: dict[str, str] | None = None, timeout: int = 300) -> int:
    env = os.environ.copy()
    env.update(extra_env or {})
    started = datetime.datetime.now().astimezone().isoformat()
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
        code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        code = 124
        stdout = exc.stdout or b""
        stderr = (exc.stderr or b"") + b"\nTIMEOUT\n"
    ended = datetime.datetime.now().astimezone().isoformat()
    (LOGS / f"{name}.stdout").write_bytes(stdout)
    (LOGS / f"{name}.stderr").write_bytes(stderr)
    (LOGS / f"{name}.json").write_text(
        json.dumps(
            {
                "cwd": str(cwd),
                "argv": argv,
                "extra_environment": extra_env or {},
                "start": started,
                "end": ended,
                "exit_code": code,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{name}: exit {code}")
    return code


go_dir = OUT / "fabric" / "compile_copy"
go_code = run(
    "B_go_compile_auto",
    ["/usr/local/go/bin/go", "build", "-mod=readonly", "./..."],
    go_dir,
    {
        "GOTOOLCHAIN": "auto",
        "GOCACHE": str(OUT / "fabric" / "build_cache"),
        "GOMODCACHE": str(OUT / "fabric" / "module_cache"),
    },
)

solc_js = Path("/home/shenxz-lab/.nvm/versions/node/v18.20.8/lib/node_modules/solc/solc.js")
if solc_js.exists():
    solc_version = run("solcjs_version", ["/usr/bin/node", str(solc_js), "--version"], OUT)
    solidity_code = run(
        "C_solidity_compile",
        [
            "/usr/bin/node",
            str(solc_js),
            "--bin",
            "--abi",
            "--optimize",
            "-o",
            str(OUT / "geth" / "compiled"),
            str(OUT / "geth" / "raw" / "SupplyChainPaper.sol"),
        ],
        OUT / "geth",
    )
else:
    solc_version = solidity_code = 127

status_path = OUT / "evidence" / "status.json"
status = json.loads(status_path.read_text(encoding="utf-8"))
status["go_compile"] = "PASS" if go_code == 0 else "FAIL"
status["solidity_compile"] = "PASS" if solidity_code == 0 else "FAIL"
status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
