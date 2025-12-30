#
# SPDX-License-Identifier: Apache-2.0
#
import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List

from django.core.exceptions import ObjectDoesNotExist

from api.services.agent import AgentService, AgentServiceError
from api.models import Agent, FabricResourceSet, Node, Port, ResourceSet

LOG = logging.getLogger(__name__)


class NodeProvisioningError(Exception):
    """Raised when node provisioning steps fail."""


@dataclass
class NodeAgentPayload:
    node: Node
    agent: Agent
    fabric_resource_set: FabricResourceSet
    resource_set: ResourceSet
    ports: Iterable[Port]
    payload: Dict

    def as_dict(self) -> Dict:
        return dict(self.payload)


class NodeProvisioner:
    """Centralizes node/agent orchestration helpers."""

    @staticmethod
    def _organize_org_name(node: Node, fabric_resource_set: FabricResourceSet) -> str:
        if node.type == "peer":
            return fabric_resource_set.name
        try:
            return fabric_resource_set.name.split(".", 1)[1]
        except IndexError:
            return fabric_resource_set.name

    @classmethod
    def build_agent_payload(cls, node_id) -> NodeAgentPayload:
        try:
            node = Node.objects.select_related(
                "fabric_resource_set__network",
                "fabric_resource_set__resource_set__agent",
            ).get(id=node_id)
        except ObjectDoesNotExist as exc:
            raise NodeProvisioningError("Node not found") from exc

        fabric_resource_set = node.fabric_resource_set
        if fabric_resource_set is None:
            raise NodeProvisioningError("Node is missing fabric resource set")
        resource_set = fabric_resource_set.resource_set
        if resource_set is None:
            raise NodeProvisioningError("Fabric resource set missing resource set")
        agent = resource_set.agent
        if agent is None:
            raise NodeProvisioningError("Resource set is not bound to an agent")
        network = fabric_resource_set.network
        if network is None:
            raise NodeProvisioningError("Organization is not attached to a network")

        ports: List[Port] = list(Port.objects.filter(node=node))
        if not ports:
            raise NodeProvisioningError("Node does not have any port mappings")

        org_name = cls._organize_org_name(node, fabric_resource_set)
        payload = {
            "status": node.status,
            "msp": node.msp,
            "tls": node.tls,
            "config_file": node.config_file,
            "type": node.type,
            "name": f"{node.name}.{org_name}",
            "bootstrap_block": network.genesisblock,
            "urls": agent.urls,
            "network_type": network.type,
            "agent_type": agent.type,
            "container_name": f"{node.name}.{org_name}",
            "ports": ports,
        }

        return NodeAgentPayload(
            node=node,
            agent=agent,
            fabric_resource_set=fabric_resource_set,
            resource_set=resource_set,
            ports=ports,
            payload=payload,
        )

    @classmethod
    def start_node(cls, node_id):
        payload = cls.build_agent_payload(node_id)
        try:
            service = AgentService(payload.payload)
            cid = service.create(payload.payload)
        except AgentServiceError as exc:
            raise NodeProvisioningError(str(exc)) from exc

        if not cid:
            raise NodeProvisioningError("Agent did not return container id")

        Node.objects.filter(id=node_id).update(cid=cid, status="running")
        return cid

