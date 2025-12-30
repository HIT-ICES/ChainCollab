#
# SPDX-License-Identifier: Apache-2.0
#
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type

from api.common.enums import HostType
from api.lib.agent.base import AgentBase
from api.lib.agent.docker import DockerAgent
from api.lib.agent.kubernetes import KubernetesAgent

LOG = logging.getLogger(__name__)


class AgentServiceError(Exception):
    """Raised when agent operations fail or are misconfigured."""


@dataclass(frozen=True)
class AgentContext:
    """Normalized payload used to initialize low-level agent implementations."""

    payload: Dict[str, Any] = field(default_factory=dict)

    @property
    def agent_type(self) -> str:
        agent_type = (self.payload or {}).get("agent_type")
        if not agent_type:
            raise AgentServiceError("Agent type is required for agent operations.")
        return str(agent_type).lower()


class AgentFactory:
    """Factory that maps agent types to concrete implementations."""

    _registry: Dict[str, Type[AgentBase]] = {
        HostType.Docker.name.lower(): DockerAgent,
        HostType.Kubernetes.name.lower(): KubernetesAgent,
    }

    @classmethod
    def create(cls, context: AgentContext) -> AgentBase:
        agent_cls = cls._registry.get(context.agent_type)
        if agent_cls is None:
            raise AgentServiceError(f"Unsupported agent type: {context.agent_type}")
        return agent_cls(context.payload)


class AgentService:
    """High level wrapper that exposes safe agent operations."""

    def __init__(self, node: Optional[Dict[str, Any]] = None):
        node = node or {}
        self._context = AgentContext(node)
        self._agent = AgentFactory.create(self._context)

    @property
    def context(self) -> AgentContext:
        return self._context

    def _call(self, method: str, *args, **kwargs):
        if not hasattr(self._agent, method):
            raise AgentServiceError(f"Agent does not implement '{method}'")
        try:
            return getattr(self._agent, method)(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            LOG.error("Agent operation %s failed: %s", method, exc)
            raise AgentServiceError(str(exc)) from exc

    def generate_config(self):
        return self._call("generate_config")

    def create(self, info):
        return self._call("create", info)

    def delete(self, *args, **kwargs):
        return self._call("delete", *args, **kwargs)

    def start(self, *args, **kwargs):
        return self._call("start", *args, **kwargs)

    def stop(self, *args, **kwargs):
        return self._call("stop", *args, **kwargs)

    def update_config(self, config_file, node_type):
        return self._call("update_config", config_file, node_type)

    def get(self, *args, **kwargs):
        return self._call("get", *args, **kwargs)

    def ca_create_custom(self, *args, **kwargs):
        return self._call("ca_create_custom", *args, **kwargs)

    def ca_start(self, *args, **kwargs):
        return self._call("ca_start", *args, **kwargs)

    def available_ports_get(self, *args, **kwargs):
        return self._call("ports_gets", *args, **kwargs)
