#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DASH_DIR = PROJECT_DIR / "dashboard"


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_cmd(cmd, *, cwd=PROJECT_DIR, check=True, env=None):
    return subprocess.run(cmd, cwd=cwd, check=check, env=env)


def exec_cmd(cmd, *, cwd=PROJECT_DIR, env=None):
    if cwd:
        os.chdir(cwd)
    os.execvpe(cmd[0], cmd, env or os.environ)


def pick_node_manager() -> str:
    override = os.environ.get("NODE_PKG_MANAGER")
    if override:
        return override
    if (DASH_DIR / "pnpm-lock.yaml").exists() and cmd_exists("pnpm"):
        return "pnpm"
    if (DASH_DIR / "yarn.lock").exists() and cmd_exists("yarn"):
        return "yarn"
    return "npm"


def venv_is_healthy(candidate: Path) -> bool:
    python_bin = candidate / "bin" / "python"
    python3_bin = candidate / "bin" / "python3"
    return (
        python_bin.exists()
        and python3_bin.exists()
        and os.access(python_bin, os.X_OK)
        and os.access(python3_bin, os.X_OK)
    )


def find_venv() -> Path | None:
    for name in (".venv", "venv"):
        candidate = PROJECT_DIR / name
        if venv_is_healthy(candidate):
            return candidate
    return None


def ensure_venv() -> Path:
    venv = find_venv()
    if venv:
        return venv
    venv = PROJECT_DIR / ".venv"
    if venv.exists():
        print(f"[newTranslator] removing broken virtualenv: {venv}")
        shutil.rmtree(venv, ignore_errors=True)
    if cmd_exists("uv"):
        run_cmd(["uv", "venv", "--seed", str(venv)])
    else:
        run_cmd(["python3", "-m", "venv", str(venv)])
    return venv


def install_deps():
    venv = ensure_venv()
    pip_bin = venv / "bin" / "pip"
    python_bin = venv / "bin" / "python"
    if not pip_bin.exists():
        if cmd_exists("uv"):
            run_cmd(["uv", "pip", "install", "-r", "requirements.txt", "--python", str(python_bin)])
            run_cmd(["uv", "pip", "install", "-e", str(PROJECT_DIR / "DSL" / "B2CDSL"), "--python", str(python_bin)])
            run_cmd(["uv", "pip", "install", "-e", str(PROJECT_DIR / "CodeGenerator" / "b2cdsl-go"), "--python", str(python_bin)])
            run_cmd(["uv", "pip", "install", "-e", str(PROJECT_DIR / "CodeGenerator" / "b2cdsl-solidity"), "--python", str(python_bin)])
        else:
            run_cmd([str(python_bin), "-m", "ensurepip"])
    if pip_bin.exists():
        run_cmd([str(pip_bin), "install", "-r", "requirements.txt"])
        run_cmd([str(pip_bin), "install", "-e", str(PROJECT_DIR / "DSL" / "B2CDSL")])
        run_cmd([str(pip_bin), "install", "-e", str(PROJECT_DIR / "CodeGenerator" / "b2cdsl-go")])
        run_cmd([str(pip_bin), "install", "-e", str(PROJECT_DIR / "CodeGenerator" / "b2cdsl-solidity")])

    if DASH_DIR.exists():
        manager = pick_node_manager()
        if manager == "pnpm":
            run_cmd(["pnpm", "install"], cwd=DASH_DIR)
        elif manager == "yarn":
            run_cmd(["yarn", "install"], cwd=DASH_DIR)
        else:
            run_cmd(["npm", "install"], cwd=DASH_DIR)


def ensure_api_deps() -> Path:
    venv = find_venv()
    if venv:
        return venv
    print("[newTranslator] virtualenv not found. Running setup...")
    install_deps()
    venv = find_venv()
    if not venv:
        print("[newTranslator] virtualenv not found after setup.")
        sys.exit(1)
    return venv


def ensure_dashboard_deps():
    if not DASH_DIR.exists():
        return
    if (DASH_DIR / "node_modules").exists():
        return
    manager = pick_node_manager()
    if manager == "pnpm":
        run_cmd(["pnpm", "install"], cwd=DASH_DIR)
    elif manager == "yarn":
        run_cmd(["yarn", "install"], cwd=DASH_DIR)
    else:
        run_cmd(["npm", "install"], cwd=DASH_DIR)


def start_api():
    venv = ensure_api_deps()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_DIR.parent)
    uvicorn_bin = venv / "bin" / "uvicorn"
    if uvicorn_bin.exists():
        cmd = [
            str(uvicorn_bin),
            "newTranslator.service.api:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "9999",
        ]
    else:
        python_bin = venv / "bin" / "python"
        cmd = [
            str(python_bin),
            "-m",
            "uvicorn",
            "newTranslator.service.api:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "9999",
        ]
    exec_cmd(cmd, env=env)


def start_dashboard():
    if not DASH_DIR.exists():
        print(f"[newTranslator] dashboard dir not found: {DASH_DIR}")
        sys.exit(1)
    ensure_dashboard_deps()
    manager = pick_node_manager()
    if manager == "pnpm":
        exec_cmd(["pnpm", "run", "dev"], cwd=DASH_DIR)
    elif manager == "yarn":
        exec_cmd(["yarn", "dev"], cwd=DASH_DIR)
    else:
        exec_cmd(["npm", "run", "dev"], cwd=DASH_DIR)


def start_all():
    start_api()


def clean_artifacts():
    for path in PROJECT_DIR.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)

    for name in ("node_modules", "dist", ".vite"):
        path = DASH_DIR / name
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    print("[newTranslator] cleaned __pycache__/node_modules/cache")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="newTranslator_devtools.sh",
        description=(
            "newTranslator dev helper for src/newTranslator.\n"
            "Use: ./newTranslator_devtools.sh <command>"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  newTranslator_devtools.sh setup\n"
            "  newTranslator_devtools.sh api\n"
            "  newTranslator_devtools.sh dashboard\n"
            "  newTranslator_devtools.sh clean\n"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Create venv, install python deps and dashboard deps.")
    sub.add_parser("api", help="Start FastAPI service via uvicorn.")
    sub.add_parser("start", help="Alias for api.")
    sub.add_parser("dashboard", help="Start dashboard dev server.")
    sub.add_parser("clean", help="Remove __pycache__/node_modules/cache.")
    sub.add_parser("help", help="Show this help.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None or args.command == "help":
        parser.print_help()
        return 0

    dispatch = {
        "setup": install_deps,
        "api": start_api,
        "start": start_api,
        "dashboard": start_dashboard,
        "clean": clean_artifacts,
    }

    handler = dispatch.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1

    handler()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
