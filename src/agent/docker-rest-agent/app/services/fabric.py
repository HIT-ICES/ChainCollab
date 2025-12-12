from typing import Tuple

from werkzeug.datastructures import ImmutableMultiDict

from ..template_lib.fabric import (
    FabricCATemplate,
    FabricOrdererTemplate,
    FabricPeerTemplate,
)
from .base import ContainerSpec, NodeProvisioner, ProvisionContext


class TemplateProvisioner(NodeProvisioner):
    template_class = None

    def __init__(self):
        self.template = self.template_class()

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


class FabricPeerProvisioner(TemplateProvisioner):
    type_name = "fabric-peer"
    template_class = FabricPeerTemplate


class FabricOrdererProvisioner(TemplateProvisioner):
    type_name = "fabric-orderer"
    template_class = FabricOrdererTemplate


class FabricCAProvisioner(TemplateProvisioner):
    type_name = "fabric-ca"
    template_class = FabricCATemplate

    def describe(self, container):
        data = super().describe(container)
        data["home"] = container.attrs.get("Mounts", [{}])[0].get("Source")
        return data
