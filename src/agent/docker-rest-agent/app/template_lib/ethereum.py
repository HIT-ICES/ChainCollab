import logging
import os
from typing import Optional, Tuple

from werkzeug.datastructures import ImmutableMultiDict

from ..config import ETH_SERVERS_PATH, ETH_TEMPLATE_PATH, CONFIG
from ..docker_client import docker_client
from ..infrastructure.ports import find_free_port, is_port_available
from ..infrastructure.storage import storage_manager
from ..services.base import ContainerSpec, ProvisionContext
from ..utils import parse_port_map, require_param


class EthereumNodeTemplate:
    def _get_network_subnet(self) -> Optional[str]:
        try:
            net = docker_client.networks.get(CONFIG.fabric_network)
            ipam = net.attrs.get("IPAM", {}).get("Config", [])
            for cfg in ipam:
                subnet = cfg.get("Subnet")
                if subnet:
                    return subnet
        except Exception:
            logging.exception("Failed to detect docker network subnet")
        return None

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

        # Use the ports from backend directly (backend has already allocated available ports)
        ports = {
            "8545/tcp": port_map.get("8545", 8545),
            "30303/tcp": port_map.get("30303", 30303),
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

    def create_system_node(self, form_data: ImmutableMultiDict) -> Tuple[ContainerSpec, ProvisionContext]:
        """
        Create a system geth node based on docker-compose.sys.yml template.
        This node acts as a bootnode with HTTP RPC enabled.
        """
        node_name = form_data.get("name", "sys_geth")
        raw_port_map = form_data.get("port_map", '{"8545": 8545, "30303": 30303}')
        port_map = parse_port_map(raw_port_map)
        if not port_map:
            raise ValueError("port_map is required for system node")

        # Setup storage paths
        sys_node_home = ETH_SERVERS_PATH / "sys" / "datadir"
        if sys_node_home.exists():
            raise ValueError("System node storage already exists")
        storage_manager.ensure_dir(sys_node_home)

        # Build Docker image
        dockerfile_path = ETH_TEMPLATE_PATH / "multi-geth-blockchain"
        try:
            docker_client.images.build(path=str(dockerfile_path), tag="geth-custom:latest", rm=True)
        except Exception as exc:
            logging.exception("Failed to build Docker image for system node")
            raise RuntimeError(f"Failed to build Docker image: {exc}")

        # Setup volumes for keystore and password
        keystore_path = dockerfile_path / "keystore"
        password_path = dockerfile_path / "password.txt"

        volumes = {
            os.path.abspath(sys_node_home): {
                "bind": "/root/.ethereum",
                "mode": "rw",
            },
            os.path.abspath(keystore_path): {
                "bind": "/root/.ethereum/keystore",
                "mode": "rw",
            },
            os.path.abspath(password_path): {
                "bind": "/root/password.txt",
                "mode": "ro",
            },
        }

        ports = {
            "8545/tcp": port_map.get("8545", 8545),
            "30303/tcp": port_map.get("30303", 30303),
        }

        netrestrict = self._get_network_subnet()
        command = [
            "--datadir=/root/.ethereum",
            "--networkid=3456",
            "--syncmode=full",
            # P2P: bootnode must enable discovery
            "--port=30303",
            "--maxpeers=50",
            # HTTP RPC for FireFly
            "--http",
            "--http.addr=0.0.0.0",
            "--http.port=8545",
            "--http.api=admin,eth,net,web3,txpool,personal",
            "--http.corsdomain=*",
            "--http.vhosts=*",
            # Unlock fixed account (only for dev/internal network)
            "--unlock=0x365acf78c44060caf3a4789d804df11e3b4aa17d",
            "--password=/root/password.txt",
            "--allow-insecure-unlock",
            "--verbosity=4",
        ]
        if netrestrict:
            command.insert(5, f"--netrestrict={netrestrict}")

        spec = ContainerSpec(
            image="geth-custom:latest",
            command=command,
            name=node_name,
            environment={},
            volumes=volumes,
            ports=ports,
            network=CONFIG.fabric_network,
            dns_search=["."],
            cpu_limit=0.5,
        )

        context = ProvisionContext(
            cleanup_paths=[str(sys_node_home)],
            metadata={
                "home": str(sys_node_home),
                "ports": ports,
                "type": "system",  # Use unified 'type' field
            },
        )
        return spec, context

    def create_org_node(self, form_data: ImmutableMultiDict) -> Tuple[ContainerSpec, ProvisionContext]:
        """
        Create an organization geth node based on docker-compose.org.yml template.
        This node connects to the system bootnode and performs PoW mining.
        """
        node_name = require_param(form_data, "name")
        sys_enode = require_param(form_data, "sys_enode")

        # Organization nodes typically don't expose HTTP RPC externally
        # but we still support custom port mapping if needed
        raw_port_map = form_data.get("port_map", '{}')
        port_map = parse_port_map(raw_port_map) if raw_port_map else {}

        # Setup storage paths
        org_node_home = ETH_SERVERS_PATH / node_name / "datadir"
        if org_node_home.exists():
            raise ValueError(f"Organization node {node_name} storage already exists")
        storage_manager.ensure_dir(org_node_home)

        # Build Docker image
        dockerfile_path = ETH_TEMPLATE_PATH / "multi-geth-blockchain"
        try:
            docker_client.images.build(path=str(dockerfile_path), tag="geth-custom:latest", rm=True)
        except Exception as exc:
            logging.exception("Failed to build Docker image for org node %s", node_name)
            raise RuntimeError(f"Failed to build Docker image: {exc}")

        volumes = {
            os.path.abspath(org_node_home): {
                "bind": "/root/.ethereum",
                "mode": "rw",
            }
        }

        # Only expose ports if specified
        ports = {}
        if port_map:
            for internal_port, external_port in port_map.items():
                ports[f"{internal_port}/tcp"] = external_port

        netrestrict = self._get_network_subnet()
        command = [
            "--datadir=/root/.ethereum",
            "--networkid=3456",
            "--syncmode=full",
            "--port=30303",
            f"--bootnodes={sys_enode}",
            # PoW mining
            "--mine",
            "--miner.threads=1",
            "--miner.gasprice=0",
            "--miner.etherbase=0x1111111111111111111111111111111111111111",
            "--verbosity=3",
        ]
        if netrestrict:
            command.insert(0, f"--netrestrict={netrestrict}")

        spec = ContainerSpec(
            image="geth-custom:latest",
            command=command,
            name=node_name,
            environment={"SYS_ENODE": sys_enode},
            volumes=volumes,
            ports=ports,
            network=CONFIG.fabric_network,
            dns_search=["."],
            # cpu_limit=0.8,
        )

        context = ProvisionContext(
            cleanup_paths=[str(org_node_home)],
            metadata={
                "home": str(org_node_home),
                "ports": ports,
                "type": "organization",  # Use unified 'type' field
                "sys_enode": sys_enode,
            },
        )
        return spec, context
