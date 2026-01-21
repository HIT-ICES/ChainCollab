#!/usr/bin/env python3
import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
APP_DIR = PROJECT_DIR / "docker-rest-agent"
PID_FILE = PROJECT_DIR / "agent.pid"


def run_cmd(cmd, *, cwd=PROJECT_DIR, check=True, env=None):
    return subprocess.run(cmd, cwd=cwd, check=check, env=env)


def exec_cmd(cmd, *, cwd=PROJECT_DIR, env=None):
    if cwd:
        os.chdir(cwd)
    os.execvpe(cmd[0], cmd, env or os.environ)


def resolve_venv_path() -> Path:
    override = os.environ.get("AGENT_VENV")
    if override:
        return Path(override).expanduser().resolve()
    if (APP_DIR / "venv").exists():
        return APP_DIR / "venv"
    if (APP_DIR / ".venv").exists():
        return APP_DIR / ".venv"
    return APP_DIR / "venv"


def ensure_venv() -> Path:
    venv_path = resolve_venv_path()
    if not venv_path.exists():
        if cmd_exists("uv"):
            run_cmd(["uv", "venv", "--seed", str(venv_path)], cwd=APP_DIR)
        else:
            run_cmd(["python3", "-m", "venv", str(venv_path)], cwd=APP_DIR)
    return venv_path


def install_deps():
    if not APP_DIR.exists():
        print(f"[agent] backend dir not found: {APP_DIR}")
        sys.exit(1)
    venv_path = ensure_venv()
    pip_bin = venv_path / "bin" / "pip"
    run_cmd([str(pip_bin), "install", "-r", "requirements.txt"], cwd=APP_DIR)


def start_backend():
    if not APP_DIR.exists():
        print(f"[agent] backend dir not found: {APP_DIR}")
        sys.exit(1)
    venv_path = resolve_venv_path()
    if not venv_path.exists():
        print("[agent] virtualenv not found. Running setup...")
        install_deps()
        venv_path = resolve_venv_path()
    python_bin = venv_path / "bin" / "python"
    gunicorn_bin = venv_path / "bin" / "gunicorn"
    if gunicorn_bin.exists():
        cmd = [str(gunicorn_bin), "server:app", "-c", "./gunicorn.conf.py"]
    else:
        cmd = [str(python_bin), "-m", "gunicorn", "server:app", "-c", "./gunicorn.conf.py"]
    exec_cmd(cmd, cwd=APP_DIR)


def _read_pid() -> int | None:
    try:
        value = PID_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not value:
        return None
    try:
        return int(value.split()[0])
    except ValueError:
        return None


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_backend():
    pid = _read_pid()
    if not pid:
        print("[agent] no agent.pid found; stop requires a background process")
        return
    if not _pid_is_running(pid):
        print(f"[agent] process not running (PID {pid})")
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(20):
        if not _pid_is_running(pid):
            print(f"[agent] stopped (PID {pid})")
            return
        time.sleep(0.1)
    print(f"[agent] still running (PID {pid})")


def status_backend():
    pid = _read_pid()
    if not pid:
        print("[agent] no agent.pid found")
        return
    if _pid_is_running(pid):
        print(f"[agent] running (PID {pid})")
    else:
        print(f"[agent] not running (PID {pid})")


def clean_artifacts():
    if APP_DIR.exists():
        for path in APP_DIR.rglob("__pycache__"):
            shutil.rmtree(path, ignore_errors=True)

    for name in ("agent.pid", "agent.log"):
        path = PROJECT_DIR / name
        if path.exists():
            try:
                path.unlink()
            except FileNotFoundError:
                continue
    print("[agent] cleaned __pycache__/pids/logs")


def archive_logs(tag: str):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_dir = PROJECT_DIR / "runtime" / "archive" / f"{timestamp}-{tag}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in ("agent.log", "agent.pid"):
        path = PROJECT_DIR / name
        if path.exists():
            shutil.copy2(path, archive_dir / name)
    print(f"[agent] archived logs -> {archive_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_devtools.sh",
        description=(
            "Agent dev helper for src/agent.\n"
            "Use: ./agent_devtools.sh <command>"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  agent_devtools.sh setup\n"
            "  agent_devtools.sh start\n"
            "  agent_devtools.sh status\n"
            "  agent_devtools.sh clean\n"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Create venv and install python deps.")
    sub.add_parser("start", help="Start agent backend in foreground.")
    sub.add_parser("stop", help="Stop agent backend using agent.pid if present.")
    sub.add_parser("restart", help="Stop (if needed) then start backend in foreground.")
    sub.add_parser("status", help="Show backend status from agent.pid.")
    sub.add_parser("clean", help="Remove __pycache__/pids/logs.")
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
        "start": start_backend,
        "stop": lambda: (stop_backend(), archive_logs("stop")),
        "restart": lambda: (stop_backend(), archive_logs("restart"), start_backend()),
        "status": status_backend,
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
