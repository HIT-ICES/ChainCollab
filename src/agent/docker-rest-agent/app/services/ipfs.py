from typing import Tuple

from werkzeug.datastructures import ImmutableMultiDict

from ..template_lib.ipfs import IPFSTemplate
from .base import ContainerSpec, NodeProvisioner, ProvisionContext


class IPFSProvisioner(NodeProvisioner):
    type_name = "ipfs-node"

    def __init__(self):
        self.template = IPFSTemplate()

    def build_spec(
        self, form_data: ImmutableMultiDict
    ) -> Tuple[ContainerSpec, ProvisionContext]:
        return self.template.render(form_data)
