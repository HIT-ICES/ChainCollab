#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import socket
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = REPO_ROOT / "src" / "runtime"
PID_FILE = RUNTIME_DIR / "devtools.pids"
LOG_FILES = {
    "newTranslator": RUNTIME_DIR / "newTranslator.log",
    "agent": RUNTIME_DIR / "agent.log",
    "backend": RUNTIME_DIR / "backend.log",
    "front": RUNTIME_DIR / "front.log",
}
SERVICE_PORTS = {
    "newTranslator": 9999,
    "agent": 7001,
    "backend": 8000,
    "front": 3000,
}
SERVICE_START_ORDER = ["newTranslator", "agent", "backend", "front"]
BACKEND_DIR = REPO_ROOT / "src" / "backend"
DASHBOARD_DIR = REPO_ROOT / "src" / "dashboard"
AGENT_DIR = REPO_ROOT / "src" / "agent" / "docker-rest-agent"
FRONT_DIR = REPO_ROOT / "src" / "front"
FRONT_DEVTOOLS = REPO_ROOT / "src" / "front" / "front_devtools.sh"
BACKEND_DEVTOOLS = REPO_ROOT / "src" / "backend" / "backend_devtools.sh"
AGENT_DEVTOOLS = REPO_ROOT / "src" / "agent" / "agent_devtools.sh"
NEW_TRANSLATOR_DEVTOOLS = REPO_ROOT / "src" / "newTranslator" / "newTranslator_devtools.sh"
BPMN_DEVTOOLS = REPO_ROOT / "src" / "bpmn-chor-app" / "bpmn_devtools.sh"
INSPECT_SRC = REPO_ROOT / "src" / "scripts" / "inspect_src.py"
GOVERNANCE_CHECK = REPO_ROOT / "src" / "scripts" / "governance_check.py"
SERVICE_DEFS = {
    "newTranslator": {
        "devtools": NEW_TRANSLATOR_DEVTOOLS,
        "args": ["start"],
        "port": 9999,
        "env": None,
    },
    "agent": {
        "devtools": AGENT_DEVTOOLS,
        "args": ["start"],
        "port": 7001,
        "env": None,
    },
    "backend": {
        "devtools": BACKEND_DEVTOOLS,
        "args": ["start"],
        "port": 8000,
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "front": {
        "devtools": FRONT_DEVTOOLS,
        "args": ["start"],
        "port": 3000,
        "env": None,
    },
}
PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
)
DEBUG_MODE = os.getenv("DEVTOOLS_DEBUG", "").lower() in ("1", "true", "yes", "on")


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def env_without_proxy(extra_env=None) -> dict[str, str]:
    env = os.environ.copy()
    for key in PROXY_ENV_KEYS:
        env.pop(key, None)
    if extra_env:
        env.update(extra_env)
    return env


def run_cmd(cmd, *, cwd=None, check=True, env=None, input_text=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        env=env_without_proxy(env),
        text=True,
        input=input_text,
    )


def run_output(cmd, *, cwd=None, env=None) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            text=True,
            capture_output=True,
            env=env_without_proxy(env),
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def ensure_dir(path: Path, label: str) -> bool:
    if not path.exists():
        print(f"[dev] {label} directory not found: {path}")
        return False
    return True


def ensure_runtime_dir():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            return False
    return True


def pids_for_port(port: int) -> list[int]:
    if not cmd_exists("lsof"):
        return []
    result = run_output(
        ["lsof", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"]
    )
    pids = []
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.append(int(line))
        except ValueError:
            continue
    return pids


def terminate_pids(pids: list[int]) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
    time.sleep(0.5)
    for pid in pids:
        if pid_is_running(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                continue


def check_ports():
    checks = [
        ("newTranslator", 9999),
        ("agent", 7001),
        ("backend", 8000),
        ("front", 3000),
    ]
    conflicts = [(name, port) for name, port in checks if not port_is_available(port)]
    if conflicts:
        for name, port in conflicts:
            print(f"[dev] Port {port} in use (service: {name})")
        answer = input("[dev] Terminate processes holding these ports? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            sys.exit(1)
        if not cmd_exists("lsof"):
            print("[dev] lsof not found; cannot auto-terminate port holders.")
            sys.exit(1)
        target_pids: set[int] = set()
        for _, port in conflicts:
            target_pids.update(pids_for_port(port))
        if not target_pids:
            print("[dev] No PIDs found for conflicting ports.")
            sys.exit(1)
        terminate_pids(sorted(target_pids))
        remaining = [(name, port) for name, port in checks if not port_is_available(port)]
        if remaining:
            for name, port in remaining:
                print(f"[dev] Port {port} still in use (service: {name})")
            sys.exit(1)


def write_pid_file(pids: dict[str, int]):
    ensure_runtime_dir()
    with PID_FILE.open("w", encoding="utf-8") as handle:
        for name, pid in pids.items():
            handle.write(f"{name} {pid}\n")


def archive_runtime_logs(tag: str):
    ensure_runtime_dir()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_dir = RUNTIME_DIR / "archive" / f"{timestamp}-{tag}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for log_path in LOG_FILES.values():
        if log_path.exists():
            shutil.copy2(log_path, archive_dir / log_path.name)
    if PID_FILE.exists():
        shutil.copy2(PID_FILE, archive_dir / PID_FILE.name)
    tasks_dir = RUNTIME_DIR / "tasks"
    if tasks_dir.exists():
        tasks_archive = archive_dir / "tasks"
        tasks_archive.mkdir(parents=True, exist_ok=True)
        for task_file in tasks_dir.glob("task-*.log"):
            shutil.copy2(task_file, tasks_archive / task_file.name)
    print(f"[dev] archived logs -> {archive_dir}")
    prune_log_archives(keep=3)


def prune_log_archives(keep: int = 3):
    archive_root = RUNTIME_DIR / "archive"
    if not archive_root.exists():
        return
    entries = [p for p in archive_root.iterdir() if p.is_dir()]
    entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in entries[keep:]:
        shutil.rmtree(old, ignore_errors=True)


def read_pid(path: Path) -> int | None:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not content:
        return None
    try:
        return int(content.split()[0])
    except ValueError:
        return None


def pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_pid(pid: int, name: str):
    if not pid_is_running(pid):
        print(f"[dev] {name} not running (PID {pid})")
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    for _ in range(20):
        if not pid_is_running(pid):
            print(f"[dev] {name} stopped (PID {pid})")
            return
        time.sleep(0.1)
    print(f"[dev] {name} still running (PID {pid})")


def spawn_service(
    name: str,
    cmd: list[str],
    *,
    cwd: Path,
    log_path: Path,
    env=None,
    log_to_file: bool = True,
    pipe_logs: bool = True,
    startup_wait: float = 1.0,
) -> int:
    ensure_runtime_dir()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8") if log_to_file else None
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=(subprocess.PIPE if log_to_file and pipe_logs else log_file),
        stderr=(subprocess.STDOUT if log_to_file and pipe_logs else log_file),
        env=env_without_proxy(env),
        start_new_session=True,
    )
    ansi_re = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

    def _pipe_to_log():
        if process.stdout is None:
            return
        for raw in iter(process.stdout.readline, b""):
            if not raw:
                break
            text = raw.decode("utf-8", errors="replace")
            cleaned = ansi_re.sub("", text)
            if log_file:
                log_file.write(cleaned)
                log_file.flush()
        if log_file:
            log_file.close()

    if log_to_file and pipe_logs:
        threading.Thread(target=_pipe_to_log, daemon=True).start()
    elif log_file:
        log_file.close()
    if startup_wait > 0:
        time.sleep(startup_wait)
    exit_code = process.poll()
    if exit_code is not None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if log_to_file:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    f"[dev] process exited early with code {exit_code} at {timestamp}\n"
                )
        print(f"[dev] {name} exited early (code {exit_code}) at {timestamp}")
    print(f"[dev] {name} started (PID {process.pid}) -> {log_path}")
    return process.pid


def monitor_processes(pids: dict[str, int]):
    def _watch(name: str, pid: int, log_path: Path):
        while True:
            time.sleep(5)
            if not pid_is_running(pid):
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                if log_path.exists():
                    with log_path.open("a", encoding="utf-8") as handle:
                        handle.write(f"[dev] {name} exited at {timestamp}\n")
                print(f"[dev] {name} exited at {timestamp}")
                return

    for name, pid in pids.items():
        log_path = LOG_FILES.get(name, RUNTIME_DIR / f"{name}.log")
        threading.Thread(target=_watch, daemon=True, args=(name, pid, log_path)).start()


def run_subtool(script: Path, args: list[str], *, env=None):
    if not script.exists():
        print(f"[dev] devtools not found: {script}")
        sys.exit(1)
    run_cmd([sys.executable, str(script), *args], cwd=script.parent, env=env)


def sudo_chmod(path: Path):
    if not path.exists():
        return
    run_cmd(["sudo", "chmod", "-R", "777", str(path)], check=False)


def sudo_remove_contents(path: Path):
    if not path.exists():
        return
    for child in path.iterdir():
        run_cmd(["sudo", "rm", "-rf", str(child)], check=False)


def remove_contents(path: Path):
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except FileNotFoundError:
                continue
            except PermissionError:
                run_cmd(["sudo", "rm", "-f", str(child)], check=False)


def list_docker_containers() -> list[str]:
    if not cmd_exists("docker"):
        return []
    output = run_output(["docker", "ps", "-a", "--format", "{{.Names}}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def list_docker_images() -> list[str]:
    if not cmd_exists("docker"):
        return []
    output = run_output(["docker", "images", "--format", "{{.Repository}}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def stop_remove_container(name: str):
    if not cmd_exists("docker"):
        return
    run_cmd(["docker", "stop", name], check=False)
    run_cmd(["docker", "rm", name], check=False)


def remove_firefly():
    if not cmd_exists("ff"):
        return
    output = run_output(["ff", "list"])
    for line in output.splitlines():
        if "cello_" not in line:
            continue
        stack = line.split()[0]
        run_cmd(["ff", "remove", stack], check=False, input_text="y\n")
    stacks_dir = Path.home() / ".firefly" / "stacks"
    if stacks_dir.exists():
        for path in stacks_dir.glob("cello_*"):
            shutil.rmtree(path, ignore_errors=True)


def run_clean():
    stop_stack()
    clean_script = REPO_ROOT / "src" / "clean.sh"
    if not clean_script.exists():
        print(f"[dev] clean.sh not found at {clean_script}")
        sys.exit(1)
    run_cmd([sys.executable, str(clean_script)])
    clean_hosts()


def run_governance_check_internal(*, json_mode: bool = False) -> int:
    if not GOVERNANCE_CHECK.exists():
        print(f"[dev] governance script not found: {GOVERNANCE_CHECK}")
        return 2
    cmd = [sys.executable, str(GOVERNANCE_CHECK)]
    if json_mode:
        cmd.append("--json")
    result = run_cmd(cmd, check=False)
    return result.returncode


def start_stack(
    monitor: bool = True,
    *,
    debug: bool = False,
    skip_governance_check: bool = False,
):
    failures: list[str] = []
    ensure_runtime_dir()
    pids: dict[str, int] = {}

    if not skip_governance_check:
        print("[dev] running governance-check before startup...")
        governance_rc = run_governance_check_internal()
        if governance_rc != 0:
            print(
                "[dev] governance-check failed. "
                "Use '--skip-governance-check' if you need to bypass once."
            )
            sys.exit(governance_rc)

    def start_service(
        name: str,
        devtools: Path,
        args: list[str],
        port: int,
        *,
        log_to_file: bool = True,
        pipe_logs: bool = True,
        env: dict[str, str] | None = None,
    ):
        if not devtools.exists():
            print(f"[dev] {name} devtools not found at {devtools}")
            failures.append(f"{name}: devtools missing")
            return
        if not port_is_available(port):
            print(f"[dev] Port {port} in use (service: {name})")
            failures.append(f"{name}: port {port} in use")
            return
        pid = spawn_service(
            name,
            [sys.executable, str(devtools), *args],
            cwd=devtools.parent,
            log_path=LOG_FILES[name],
            log_to_file=log_to_file,
            pipe_logs=pipe_logs,
            env=env,
            startup_wait=1.0 if debug else 0.0,
        )
        if debug:
            time.sleep(0.2)
        if not pid_is_running(pid):
            failures.append(f"{name}: exited early")
            return
        pids[name] = pid

    pipe_logs = monitor
    print("[dev] startup stack")
    for service_name in SERVICE_START_ORDER:
        spec = SERVICE_DEFS[service_name]
        start_service(
            service_name,
            spec["devtools"],
            spec["args"],
            spec["port"],
            pipe_logs=pipe_logs,
            env=spec["env"],
        )

    write_pid_file(pids)
    print(f"[dev] wrote PID file -> {PID_FILE}")
    if monitor:
        monitor_processes(pids)
        try:
            last_status: dict[str, str] = {}
            while True:
                for name, pid in pids.items():
                    status = "running" if pid_is_running(pid) else "stopped"
                    if last_status.get(name) != status:
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"[dev] {timestamp} {name} {status}")
                        last_status[name] = status
                time.sleep(5)
        except KeyboardInterrupt:
            print("[dev] ctrl+c received, running clean")
            run_clean()
            return
    if failures:
        print("[dev] start summary: some services failed")
        for item in failures:
            print(f"  - {item}")


def stop_stack():
    if not PID_FILE.exists():
        print(f"[dev] PID file not found: {PID_FILE}")
        return
    entries: list[tuple[str, int]] = []
    for line in PID_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        name, pid_str = parts[0], parts[1]
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        entries.append((name, pid))

    if not entries:
        print(f"[dev] No valid PIDs found in {PID_FILE}")
        return

    for name, pid in entries:
        stop_pid(pid, name)

    archive_runtime_logs("down")

    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        return


def show_status():
    entries: dict[str, int] = {}
    if PID_FILE.exists():
        for line in PID_FILE.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            try:
                entries[parts[0]] = int(parts[1])
            except ValueError:
                continue

    print("Stack Status")
    print("============")
    headers = ("service", "pid", "pid_alive", "port", "port_busy", "log")
    print(f"{headers[0]:<14} {headers[1]:<8} {headers[2]:<10} {headers[3]:<6} {headers[4]:<10} {headers[5]}")
    print(f"{'-'*14} {'-'*8} {'-'*10} {'-'*6} {'-'*10} {'-'*30}")
    for name in ("newTranslator", "agent", "backend", "front"):
        pid = entries.get(name)
        pid_str = str(pid) if pid else "-"
        alive = "yes" if (pid and pid_is_running(pid)) else "no"
        port = SERVICE_PORTS[name]
        port_busy = "yes" if not port_is_available(port) else "no"
        log_path = LOG_FILES.get(name, RUNTIME_DIR / f"{name}.log")
        print(f"{name:<14} {pid_str:<8} {alive:<10} {port:<6} {port_busy:<10} {log_path}")

    tasks_dir = RUNTIME_DIR / "tasks"
    task_count = len(list(tasks_dir.glob("task-*.log"))) if tasks_dir.exists() else 0
    print(f"\nRuntime task logs: {task_count} ({tasks_dir})")
    print(f"PID file: {'present' if PID_FILE.exists() else 'missing'} ({PID_FILE})")


def restart_stack(skip_governance_check: bool = False):
    stop_stack()
    run_clean()
    start_stack(skip_governance_check=skip_governance_check)


def add_host_mapping(hosts: list[str]):
    if not hosts:
        print("Usage: devtools.sh host <hostname> [hostname...]")
        sys.exit(1)
    for host in hosts:
        run_cmd(
            ["sudo", "tee", "-a", "/etc/hosts"],
            input_text=f"127.0.0.1 {host}\n",
            check=False,
        )
        print(f"＋ Added {host} to /etc/hosts")


def clean_hosts():
    hosts_path = Path("/etc/hosts")
    try:
        content = hosts_path.read_text(encoding="utf-8")
    except PermissionError:
        content = run_output(["cat", str(hosts_path)])
    if not content:
        print("[dev] Could not read /etc/hosts")
        return
    pattern = re.compile(r"^(ca\\.|peer|orderer)", re.IGNORECASE)
    filtered_lines = []
    removed = 0
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            filtered_lines.append(line)
            continue
        parts = stripped.split()
        hosts = parts[1:] if len(parts) > 1 else []
        if any(pattern.match(host) for host in hosts):
            removed += 1
            continue
        filtered_lines.append(line)
    if removed == 0:
        print("[dev] No host entries to clean")
        return
    new_content = "\n".join(filtered_lines) + "\n"
    run_cmd(
        ["sudo", "tee", str(hosts_path)],
        input_text=new_content,
        check=False,
    )
    print(f"[dev] Cleaned {removed} host entries from /etc/hosts")


def inspect_src(json_mode: bool, write_path: str):
    if not INSPECT_SRC.exists():
        print(f"[dev] inspect script not found: {INSPECT_SRC}")
        sys.exit(1)
    cmd = [sys.executable, str(INSPECT_SRC)]
    if json_mode:
        cmd.append("--json")
    if write_path:
        cmd.extend(["--write", write_path])
    run_cmd(cmd, check=False)


def governance_check(json_mode: bool):
    return run_governance_check_internal(json_mode=json_mode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devtools.sh",
        description=(
            "Developer control helper.\n"
            "Run from repo root or use the full path: ./src/devtools.sh <command>"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  devtools.sh clean\n"
            "  devtools.sh up\n"
            "  devtools.sh down\n"
            "  devtools.sh status\n"
            "  devtools.sh backend\n"
            "  devtools.sh front help\n"
            "  devtools.sh front dev -- --host 0.0.0.0\n"
            "  devtools.sh host cello.com org.com\n"
            "  devtools.sh inspect-src --json\n"
            "  devtools.sh governance-check\n"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("clean", help="Run clean.sh (storage, pgdata, docker, firefly).")
    up_parser = sub.add_parser(
        "up",
        help="Start stack: newTranslator -> agent -> backend -> front.",
    )
    up_parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Do not monitor processes after startup.",
    )
    up_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable startup waits for debugging.",
    )
    up_parser.add_argument(
        "--skip-governance-check",
        action="store_true",
        help="Skip pre-start governance validation once.",
    )
    sub.add_parser("down", help="Stop stack using PIDs from runtime file.")
    restart_parser = sub.add_parser("restart", help="Run down -> clean -> up.")
    restart_parser.add_argument(
        "--skip-governance-check",
        action="store_true",
        help="Skip pre-start governance validation once.",
    )
    sub.add_parser("status", help="Show process and port status for core stack.")
    front_parser = sub.add_parser("front", help="Proxy to front_devtools.sh.")
    front_parser.add_argument("extra", nargs=argparse.REMAINDER)
    agent_parser = sub.add_parser("agent", help="Proxy to agent_devtools.sh.")
    agent_parser.add_argument("extra", nargs=argparse.REMAINDER)
    db_parser = sub.add_parser("db", help="Proxy to backend_devtools.sh db.")
    db_parser.add_argument("extra", nargs=argparse.REMAINDER)
    prepare_parser = sub.add_parser("prepare-api", help="Proxy to backend_devtools.sh prepare-api.")
    prepare_parser.add_argument("extra", nargs=argparse.REMAINDER)
    api_parser = sub.add_parser("api", help="Proxy to backend_devtools.sh api.")
    api_parser.add_argument("extra", nargs=argparse.REMAINDER)
    backend_parser = sub.add_parser("backend", help="Proxy to backend_devtools.sh backend.")
    backend_parser.add_argument("extra", nargs=argparse.REMAINDER)
    export_er_parser = sub.add_parser("export-er", help="Proxy to backend_devtools.sh export-er.")
    export_er_parser.add_argument("extra", nargs=argparse.REMAINDER)
    export_dot_parser = sub.add_parser("export-er-dot", help="Proxy to backend_devtools.sh export-er-dot.")
    export_dot_parser.add_argument("extra", nargs=argparse.REMAINDER)
    new_translator_parser = sub.add_parser("new-translator", help="Proxy to newTranslator_devtools.sh.")
    new_translator_parser.add_argument("extra", nargs=argparse.REMAINDER)
    bpmn_parser = sub.add_parser("bpmn", help="Proxy to bpmn_devtools.sh.")
    bpmn_parser.add_argument("extra", nargs=argparse.REMAINDER)
    inspect_parser = sub.add_parser("inspect-src", help="Inspect src module layout.")
    inspect_parser.add_argument("--json", action="store_true", help="Print JSON format.")
    inspect_parser.add_argument("--write", type=str, default="", help="Write JSON snapshot path.")
    governance_parser = sub.add_parser("governance-check", help="Check src module manifest consistency.")
    governance_parser.add_argument("--json", action="store_true", help="Print JSON format.")
    sub.add_parser("help", help="Show this help.")

    host_parser = sub.add_parser("host", help="Append hostnames to /etc/hosts.")
    host_parser.add_argument("names", nargs="+")
    sub.add_parser("host-clean", help="Remove dev host entries from /etc/hosts.")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    dispatch = {
        "clean": run_clean,
        "down": stop_stack,
        "status": show_status,
    }

    passthrough = {
        "front": (FRONT_DEVTOOLS, ["help"]),
        "agent": (AGENT_DEVTOOLS, ["help"]),
        "new-translator": (NEW_TRANSLATOR_DEVTOOLS, ["help"]),
        "bpmn": (BPMN_DEVTOOLS, ["help"]),
        "db": (BACKEND_DEVTOOLS, ["db"]),
        "prepare-api": (BACKEND_DEVTOOLS, ["prepare-api"]),
        "api": (BACKEND_DEVTOOLS, ["api"]),
        "backend": (BACKEND_DEVTOOLS, ["backend"]),
        "export-er": (BACKEND_DEVTOOLS, ["export-er"]),
        "export-er-dot": (BACKEND_DEVTOOLS, ["export-er-dot"]),
    }

    if args.command == "host":
        add_host_mapping(args.names)
        return 0
    if args.command == "host-clean":
        clean_hosts()
        return 0
    if args.command == "help":
        parser.print_help()
        return 0
    if args.command == "inspect-src":
        inspect_src(args.json, args.write)
        return 0
    if args.command == "governance-check":
        return governance_check(args.json)
    if args.command == "restart":
        restart_stack(
            skip_governance_check=args.skip_governance_check,
        )
        return 0

    if args.command in passthrough:
        script, default_args = passthrough[args.command]
        extra = getattr(args, "extra", [])
        if extra and extra[0] == "--":
            extra = extra[1:]
        run_subtool(script, extra if extra else default_args)
        return 0

    if args.command == "up":
        start_stack(
            monitor=not args.no_monitor,
            debug=args.debug or DEBUG_MODE,
            skip_governance_check=args.skip_governance_check,
        )
        return 0

    handler = dispatch.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1

    handler()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
