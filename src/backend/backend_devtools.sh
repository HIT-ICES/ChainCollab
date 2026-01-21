#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
import time
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_cmd(cmd, *, cwd=PROJECT_DIR, check=True, env=None):
    return subprocess.run(cmd, cwd=cwd, check=check, env=env)


def exec_cmd(cmd, *, cwd=PROJECT_DIR, env=None):
    if cwd:
        os.chdir(cwd)
    os.execvpe(cmd[0], cmd, env or os.environ)


def env_with_venv(venv: Path) -> dict:
    env = os.environ.copy()
    venv_bin = str(venv / "bin")
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    return env


def docker_compose_base_cmd() -> list[str] | None:
    if cmd_exists("docker-compose"):
        return ["docker-compose"]
    if cmd_exists("docker"):
        return ["docker", "compose"]
    return None


def find_venv() -> Path | None:
    for name in (".venv", "venv"):
        candidate = PROJECT_DIR / name
        if (candidate / "bin" / "python").exists():
            return candidate
    return None


def ensure_venv() -> Path:
    venv = find_venv()
    if venv:
        return venv
    venv = PROJECT_DIR / ".venv"
    if cmd_exists("uv"):
        run_cmd(["uv", "venv", "--seed", str(venv)])
    else:
        run_cmd(["python3", "-m", "venv", str(venv)])
    return venv


def install_deps():
    venv = ensure_venv()
    pip_bin = venv / "bin" / "pip"
    run_cmd([str(pip_bin), "install", "-r", "requirements.txt"])


def run_manage(args: list[str]):
    venv = find_venv()
    if not venv:
        print("[backend] virtualenv not found. Running setup...")
        install_deps()
        venv = find_venv()
        if not venv:
            print("[backend] virtualenv not found after setup.")
            sys.exit(1)
    python_bin = venv / "bin" / "python"
    print(f"[backend] run manage.py {' '.join(args)}", flush=True)
    run_cmd([str(python_bin), "manage.py", *args], env=env_with_venv(venv))


def start_db():
    base = docker_compose_base_cmd()
    if not base:
        print("[backend] docker compose not found")
        sys.exit(1)
    print("[backend] starting database (docker compose up -d)", flush=True)
    run_cmd(base + ["up", "-d"])
    print("[backend] database start complete", flush=True)


def stop_db():
    base = docker_compose_base_cmd()
    if not base:
        print("[backend] docker compose not found")
        sys.exit(1)
    print("[backend] stopping database (docker compose down)", flush=True)
    run_cmd(base + ["down"], check=False)


def prepare_api():
    print("[backend] prepare_api: makemigrations", flush=True)
    run_manage(["makemigrations"])
    print("[backend] prepare_api: migrate", flush=True)
    run_manage(["migrate"])


def start_api():
    print("[backend] start_api: runserver 0.0.0.0:8000", flush=True)
    venv = find_venv()
    if not venv:
        print("[backend] virtualenv not found. Running setup...")
        install_deps()
        venv = find_venv()
        if not venv:
            print("[backend] virtualenv not found after setup.")
            sys.exit(1)
    python_bin = venv / "bin" / "python"
    exec_cmd(
        [str(python_bin), "manage.py", "runserver", "0.0.0.0:8000"],
        env=env_with_venv(venv),
    )


def start_backend():
    print("[backend] start_backend: db -> prepare_api -> api", flush=True)
    try:
        start_db()
        print("[backend] start_backend: sleep 1s before prepare_api", flush=True)
        time.sleep(1)
        print("[backend] start_backend: prepare_api", flush=True)
        prepare_api()
        print("[backend] start_backend: start_api", flush=True)
        start_api()
    except Exception as exc:
        print(f"[backend] start_backend failed: {exc}", flush=True)
        raise


def export_er():
    run_manage(["graph_models", "-a", "-g", "-o", "er.png"])


def export_er_dot():
    run_manage(["graph_models", "-a", "-o", "er.dot"])


def clean_artifacts():
    for path in PROJECT_DIR.rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
    for path in PROJECT_DIR.glob("*.pyc"):
        try:
            path.unlink()
        except FileNotFoundError:
            continue
    print("[backend] cleaned __pycache__/pyc")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backend_devtools.sh",
        description=(
            "Backend dev helper for src/backend.\n"
            "Use: ./backend_devtools.sh <command>"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  backend_devtools.sh setup\n"
            "  backend_devtools.sh db\n"
            "  backend_devtools.sh api\n"
            "  backend_devtools.sh backend\n"
            "  backend_devtools.sh export-er\n"
            "  backend_devtools.sh clean\n"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Create venv and install requirements.")
    sub.add_parser("clean", help="Remove __pycache__/pyc.")
    sub.add_parser("db", help="Start database via docker compose.")
    sub.add_parser("db-down", help="Stop database (docker compose down).")
    sub.add_parser("prepare-api", help="makemigrations + migrate.")
    sub.add_parser("api", help="Run Django dev server.")
    sub.add_parser("backend", help="db + prepare-api + api.")
    sub.add_parser("start", help="Alias for backend (db + prepare-api + api).")
    sub.add_parser("export-er", help="Export ER diagram as er.png.")
    sub.add_parser("export-er-dot", help="Export ER diagram as er.dot.")
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
        "clean": clean_artifacts,
        "db": start_db,
        "db-down": stop_db,
        "prepare-api": prepare_api,
        "api": start_api,
        "backend": start_backend,
        "start": start_backend,
        "export-er": export_er,
        "export-er-dot": export_er_dot,
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
