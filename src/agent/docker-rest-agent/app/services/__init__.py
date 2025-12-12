from typing import Dict

from .fabric import FabricPeerProvisioner, FabricOrdererProvisioner, FabricCAProvisioner
from .ethereum import EthereumNodeProvisioner
from .ipfs import IPFSProvisioner
from .base import NodeProvisioner

PROVISIONERS: Dict[str, NodeProvisioner] = {
    "fabric-peer": FabricPeerProvisioner(),
    "fabric-orderer": FabricOrdererProvisioner(),
    "eth-node": EthereumNodeProvisioner(),
    "fabric-ca": FabricCAProvisioner(),
    "ipfs-node": IPFSProvisioner(),
}


def get_provisioner(node_type: str) -> NodeProvisioner:
    provisioner = PROVISIONERS.get(node_type)
    if not provisioner:
        raise ValueError(f"Unsupported node type '{node_type}'")
    return provisioner
