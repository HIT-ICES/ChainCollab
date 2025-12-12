from dataclasses import dataclass

from ..config import CONFIG


@dataclass
class NetworkConfig:
    default_name: str = CONFIG.fabric_network


network_config = NetworkConfig()
