#!/usr/bin/env python3
import argparse
import re
import shutil
import subprocess
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
AGENT_DIR = SRC_DIR / "agent" / "docker-rest-agent"
BACKEND_DIR = SRC_DIR / "backend"


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_cmd(cmd, *, check=True, input_text=None):
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        input=input_text,
    )


def run_output(cmd) -> str:
    try:
        result = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


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


def list_docker_volumes() -> list[str]:
    if not cmd_exists("docker"):
        return []
    output = run_output(["docker", "volume", "ls", "--format", "{{.Name}}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def stop_remove_container(name: str):
    if not cmd_exists("docker"):
        return
    run_cmd(["docker", "stop", name], check=False)
    run_cmd(["docker", "rm", name], check=False)


def remove_firefly():
    print("Remove Firefly")
    if not cmd_exists("ff"):
        print("ff not found, skip Firefly cleanup")
        return
    output = run_output(["ff", "list"])
    for line in output.splitlines():
        if "cello_" not in line:
            continue
        stack = line.split()[0]
        run_cmd(["ff", "remove", stack], check=False, input_text="y\n")


def remove_oracle_related_volumes():
    print("Remove Docker Volumes (oracle/chainlink/cdmn)")
    # 仅清理本项目会创建的卷，避免误删其他业务卷。
    pattern = re.compile(
        r"^(03-ocr-multinode_pgdata[1-4]|03-ocr-multinode_pgdatabootstrap|chainlink_pgdata|cello-.*|cello_.*)$"
    )
    for volume in list_docker_volumes():
        if not pattern.search(volume):
            continue
        print(f"Removing volume: {volume}")
        run_cmd(["docker", "volume", "rm", "-f", volume], check=False)


def main():
    parser = argparse.ArgumentParser(
        description="Project clean script",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--keep-volumes",
        action="store_true",
        help="Keep docker volumes created by Chainlink/CDMN stack.",
    )
    args = parser.parse_args()

    print("Remove Storage")
    storage_dir = AGENT_DIR / "storage"
    ca_storage = AGENT_DIR / "CA_related" / "storage" / "fabric-ca-servers"
    sudo_chmod(ca_storage)
    sudo_chmod(storage_dir)
    sudo_remove_contents(storage_dir)

    print("Remove Fabric CA storage")
    sudo_chmod(ca_storage)
    sudo_remove_contents(ca_storage)

    print("Remove Ethereum storage")
    eth_storage = AGENT_DIR / "eth" / "storage" / "servers"
    sudo_chmod(eth_storage)
    sudo_remove_contents(eth_storage)

    print("Remove opt/cello")
    remove_contents(BACKEND_DIR / "opt" / "cello")

    print("Remove opt/chaincode")
    remove_contents(BACKEND_DIR / "opt" / "chaincode")
    remove_contents(BACKEND_DIR / "opt" / "ethereum-contracts")

    print("Remove pgdata")
    pgdata_dir = BACKEND_DIR / "pgdata"
    sudo_chmod(pgdata_dir)
    sudo_remove_contents(pgdata_dir)

    print("Remove py migrations")
    migrations_dir = BACKEND_DIR / "api" / "migrations"
    for path in migrations_dir.glob("*_auto_*.py"):
        run_cmd(["sudo", "rm", "-f", str(path)], check=False)

    remove_firefly()

    print("Remove runtime logs")
    runtime_dir = SRC_DIR / "runtime"
    if runtime_dir.exists():
        for path in runtime_dir.glob("*.log"):
            try:
                path.unlink()
            except FileNotFoundError:
                continue
        for path in runtime_dir.glob("*.pids"):
            try:
                path.unlink()
            except FileNotFoundError:
                continue
        remove_contents(runtime_dir / "tasks")
        remove_contents(runtime_dir / "newTranslator")

    print("Remove Docker Container")
    pattern = re.compile(
        r"(com$|edu\.cn$|tech\.cn$|org\.com$|geth|ethereum|chainlink|cdmn|oracle|mybootnode|bootnode)"
    )
    for name in list_docker_containers():
        if pattern.search(name):
            print(f"Stopping and removing container: {name}")
            stop_remove_container(name)

    print("Remove dev images")
    for image in list_docker_images():
        if image.startswith("dev"):
            print(f"Removing image: {image}")
            run_cmd(["docker", "rmi", image], check=False)

    print("Remove DB")
    stop_remove_container("cello-postgres")

    print("Remove Redis")
    stop_remove_container("cello-redis")

    if not args.keep_volumes:
        remove_oracle_related_volumes()
    else:
        print("Skip Docker volume cleanup (--keep-volumes)")

    print("Finished cleaning")


if __name__ == "__main__":
    main()
