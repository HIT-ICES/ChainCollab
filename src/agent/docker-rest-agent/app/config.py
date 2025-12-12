import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AgentConfig:
    docker_url: str = os.getenv("DOCKER_URL", "unix:///var/run/docker.sock")
    storage_path: str = os.getenv("STORAGE_PATH", str(BASE_DIR / "storage"))
    ca_storage_path: str = os.getenv(
        "CA_STORAGE_PATH", str(BASE_DIR / "CA_related" / "storage")
    )
    ca_template_path: str = os.getenv(
        "CA_TEMPLATE_PATH", str(BASE_DIR / "CA_related" / "template")
    )
    eth_storage_path: str = os.getenv("ETH_STORAGE_PATH", str(BASE_DIR / "eth" / "storage"))
    eth_template_path: str = os.getenv("ETH_TEMPLATE_PATH", str(BASE_DIR / "eth" / "template"))
    fabric_network: str = os.getenv("FABRIC_NETWORK_NAME", "cello-net")
    dev_mode: bool = _env_flag("AGENT_DEV_MODE")


CONFIG = AgentConfig()

STORAGE_PATH = Path(CONFIG.storage_path)
STORAGE_PATH.mkdir(parents=True, exist_ok=True)
FABRIC_STORAGE_PATH = STORAGE_PATH / "fabric"
FABRIC_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
FABRIC_PRODUCTION_PATH = STORAGE_PATH / "production"
FABRIC_PRODUCTION_PATH.mkdir(parents=True, exist_ok=True)

CA_STORAGE_PATH = Path(CONFIG.ca_storage_path)
CA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
CA_TEMPLATE_PATH = Path(CONFIG.ca_template_path)
CA_TEMPLATE_PATH.mkdir(parents=True, exist_ok=True)
CA_SERVERS_PATH = CA_STORAGE_PATH / "fabric-ca-servers"
CA_SERVERS_PATH.mkdir(parents=True, exist_ok=True)

ETH_STORAGE_PATH = Path(CONFIG.eth_storage_path)
ETH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
ETH_TEMPLATE_PATH = Path(CONFIG.eth_template_path)
ETH_TEMPLATE_PATH.mkdir(parents=True, exist_ok=True)
ETH_SERVERS_PATH = ETH_STORAGE_PATH / "servers"
ETH_SERVERS_PATH.mkdir(parents=True, exist_ok=True)
