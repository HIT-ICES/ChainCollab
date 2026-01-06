from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..infrastructure.runtime import runtime
from ..infrastructure.storage import storage_manager
from ..utils import ValidationError


@dataclass
class ContainerSpec:
    image: str
    command: Any
    name: str
    environment: Dict[str, Any]
    volumes: Any
    ports: Dict[str, Any]
    network: str
    detach: bool = True
    tty: bool = True
    stdin_open: bool = True
    dns_search: Optional[List[str]] = None
    cpu_limit: Optional[float] = None


@dataclass
class ProvisionContext:
    cleanup_paths: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NodeProvisioner(ABC):
    type_name: str

    @abstractmethod
    def build_spec(self, form_data) -> Tuple[ContainerSpec, ProvisionContext]:
        raise NotImplementedError

    def provision(self, form_data):
        container = None
        spec = context = None
        try:
            spec, context = self.build_spec(form_data)
            container = runtime.run(spec)
            extra = self.post_create(container, context) or {}
            data = self.build_response(container, context, extra)
            return data
        except ValidationError:
            if context:
                self.cleanup(context)
            raise
        except Exception as exc:
            if container:
                runtime.remove(container, force=True)
            if context:
                self.cleanup(context)
            raise RuntimeError(f"Provisioning {self.type_name} failed: {exc}")

    def cleanup(self, context: ProvisionContext):
        storage_manager.cleanup(context.cleanup_paths)

    def build_response(
        self, container, context: ProvisionContext, extra: Dict[str, Any]
    ) -> Dict[str, Any]:
        data = {
            "id": container.id,
            "name": container.name,
            "status": container.status,
            "node_type": self.type_name,
        }
        data.update(context.metadata)
        data.update(extra)
        return data

    def describe(self, container) -> Dict[str, Any]:
        container.reload()
        return {
            "id": container.id,
            "name": container.name,
            "status": container.status,
            "image": str(container.image),
            "ports": container.attrs.get("NetworkSettings", {}).get("Ports"),
        }

    def post_create(self, container, context: ProvisionContext):
        """Hook to run after container creation."""
        return {}
