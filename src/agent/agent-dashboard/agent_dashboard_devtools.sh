#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def pick_node_manager() -> str:
    override = os.environ.get("NODE_PKG_MANAGER")
    if override:
        return override
    if (PROJECT_DIR / "pnpm-lock.yaml").exists() and cmd_exists("pnpm"):
        return "pnpm"
    if (PROJECT_DIR / "yarn.lock").exists() and cmd_exists("yarn"):
        return "yarn"
    return "npm"


def run_cmd(cmd, *, cwd=PROJECT_DIR, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check)


def exec_cmd(cmd, *, cwd=PROJECT_DIR, env=None):
    if cwd:
        os.chdir(cwd)
    os.execvpe(cmd[0], cmd, env or os.environ)


def install_deps():
    manager = pick_node_manager()
    if manager == "pnpm":
        run_cmd(["pnpm", "install"])
    elif manager == "yarn":
        run_cmd(["yarn", "install"])
    else:
        run_cmd(["npm", "install"])


def ensure_deps():
    if (PROJECT_DIR / "node_modules").exists():
        return
    install_deps()


def run_script(script: str, extra_args: list[str]):
    manager = pick_node_manager()
    if manager == "pnpm":
        cmd = ["pnpm", "run", script]
        if extra_args:
            cmd.extend(["--", *extra_args])
    elif manager == "yarn":
        cmd = ["yarn", script, *extra_args]
    else:
        cmd = ["npm", "run", script]
        if extra_args:
            cmd.extend(["--", *extra_args])
    exec_cmd(cmd)


def clean_artifacts():
    for name in ("node_modules", "dist", ".vite"):
        path = PROJECT_DIR / name
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    print("[agent-dashboard] cleaned node_modules/dist/.vite")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_dashboard_devtools.sh",
        description=(
            "Agent dashboard dev helper for src/agent/agent-dashboard.\n"
            "Use: ./agent_dashboard_devtools.sh <command> [-- extra args]"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  agent_dashboard_devtools.sh setup\n"
            "  agent_dashboard_devtools.sh dev\n"
            "  agent_dashboard_devtools.sh build\n"
            "  agent_dashboard_devtools.sh clean\n"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Install dependencies.")
    sub.add_parser("clean", help="Remove node_modules/dist/.vite.")
    sub.add_parser("help", help="Show this help.")

    for name, help_text in (
        ("dev", "Run dev server (npm run dev)."),
        ("start", "Alias for dev."),
        ("build", "Build dashboard assets."),
        ("lint", "Run lint."),
        ("preview", "Run preview server."),
    ):
        parser_cmd = sub.add_parser(name, help=help_text)
        parser_cmd.add_argument("extra", nargs=argparse.REMAINDER)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None or args.command == "help":
        parser.print_help()
        return 0

    if args.command == "setup":
        install_deps()
        return 0
    if args.command == "clean":
        clean_artifacts()
        return 0

    if args.command == "start":
        args.command = "dev"

    if hasattr(args, "extra"):
        extra_args = args.extra
        if extra_args and extra_args[0] == "--":
            extra_args = extra_args[1:]
    else:
        extra_args = []

    ensure_deps()
    run_script(args.command, extra_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
