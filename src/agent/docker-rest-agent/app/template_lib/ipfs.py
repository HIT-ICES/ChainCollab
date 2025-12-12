import os
from typing import Tuple

from werkzeug.datastructures import ImmutableMultiDict

from ..config import CONFIG, STORAGE_PATH
from ..infrastructure.ports import find_free_port, is_port_available
from ..infrastructure.storage import storage_manager
from ..services.base import ContainerSpec, ProvisionContext
from ..utils import parse_port_map, require_param


class IPFSTemplate:
    def render(self, form_data: ImmutableMultiDict) -> Tuple[ContainerSpec, ProvisionContext]:
        node_name = require_param(form_data, "name")
        raw_port_map = form_data.get(
            "port_map", '{"5001": 5001, "4001": 4001, "8080": 8080}'
        )
        port_map = parse_port_map(raw_port_map)
        ports = self._resolve_ports(port_map)

        ipfs_home = storage_manager.ensure_dir(STORAGE_PATH / "ipfs" / node_name)

        spec = ContainerSpec(
            image="ipfs/go-ipfs:latest",
            command=None,
            name=node_name,
            environment={},
            volumes={
                os.path.abspath(ipfs_home): {
                    "bind": "/data/ipfs",
                    "mode": "rw",
                }
            },
            ports=ports,
            network=CONFIG.fabric_network,
            dns_search=["."],
        )
        context = ProvisionContext(
            cleanup_paths=[str(ipfs_home)],
            metadata={"home": str(ipfs_home), "ports": ports},
        )
        return spec, context

    def _resolve_ports(self, port_map):
        resolved = {}
        for internal, default in (("5001", 5001), ("4001", 4001), ("8080", 8080)):
            target = int(port_map.get(internal, default))
            resolved[f"{internal}/tcp"] = (
                target if is_port_available(target) else find_free_port()
            )
        return resolved
