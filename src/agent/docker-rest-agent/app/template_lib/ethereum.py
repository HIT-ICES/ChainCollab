import logging
import os
from typing import Tuple

from werkzeug.datastructures import ImmutableMultiDict

from ..config import ETH_SERVERS_PATH, ETH_TEMPLATE_PATH, CONFIG
from ..docker_client import docker_client
from ..infrastructure.ports import find_free_port, is_port_available
from ..infrastructure.storage import storage_manager
from ..services.base import ContainerSpec, ProvisionContext
from ..utils import parse_port_map, require_param


class EthereumNodeTemplate:
    def render(self, form_data: ImmutableMultiDict) -> Tuple[ContainerSpec, ProvisionContext]:
        node_name = require_param(form_data, "name")
        raw_port_map = form_data.get("port_map", '{"8545": 8545, "30303": 30303}')
        port_map = parse_port_map(raw_port_map)
        if not port_map:
            raise ValueError("port_map is required for ethereum node")

        eth_node_home = ETH_SERVERS_PATH / node_name
        if eth_node_home.exists():
            raise ValueError("Node storage already exists")
        storage_manager.ensure_dir(eth_node_home)

        dockerfile_path = ETH_TEMPLATE_PATH / "my-geth-blockchain"
        try:
            docker_client.images.build(path=str(dockerfile_path), tag="test:latest", rm=True)
        except Exception as exc:
            logging.exception("Failed to build Docker image for eth node %s", node_name)
            raise RuntimeError(f"Failed to build Docker image: {exc}")

        def get_port(port):
            return port if is_port_available(port) else find_free_port()

        ports = {
            "8545/tcp": get_port(port_map.get("8545", 8545)),
            "30303/tcp": get_port(port_map.get("30303", 30303)),
        }

        spec = ContainerSpec(
            image="ethereum/client-go:v1.10.1",
            command=[
                "--http",
                "--http.addr=0.0.0.0",
                "--http.port=8545",
                "--http.api=admin,eth,miner,web3,personal,net,txpool",
                "--networkid=3456",
                "--http.corsdomain=*",
                "--http.vhosts=*",
                "--nodiscover",
                "--mine",
                "--miner.threads=1",
                "--miner.etherbase=0x365acf78c44060caf3a4789d804df11e3b4aa17d",
                "--allow-insecure-unlock",
            ],
            name=node_name,
            environment={},
            volumes={
                os.path.abspath(eth_node_home): {
                    "bind": "/root/.ethereum",
                    "mode": "rw",
                }
            },
            ports=ports,
            network=CONFIG.fabric_network,
            dns_search=["."],
        )
        context = ProvisionContext(
            cleanup_paths=[str(eth_node_home)],
            metadata={"home": str(eth_node_home), "ports": ports},
        )
        return spec, context
