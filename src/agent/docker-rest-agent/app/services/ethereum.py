from typing import Tuple

from werkzeug.datastructures import ImmutableMultiDict

from ..template_lib.ethereum import EthereumNodeTemplate
from .base import ContainerSpec, NodeProvisioner, ProvisionContext


class EthereumNodeProvisioner(NodeProvisioner):
    type_name = "eth-node"

    def __init__(self):
        self.template = EthereumNodeTemplate()

    def build_spec(
        self, form_data: ImmutableMultiDict
    ) -> Tuple[ContainerSpec, ProvisionContext]:
        return self.template.render(form_data)

    def describe(self, container):
        data = super().describe(container)
        mounts = container.attrs.get("Mounts", [])
        data["mounts"] = [
            {"source": mount.get("Source"), "destination": mount.get("Destination")}
            for mount in mounts
        ]
        return data
