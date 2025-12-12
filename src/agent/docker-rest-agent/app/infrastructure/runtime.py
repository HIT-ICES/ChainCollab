from typing import Any

from ..docker_client import docker_client


class ContainerRuntime:
    def run(self, spec) -> Any:
        return docker_client.containers.run(
            spec.image,
            spec.command,
            detach=spec.detach,
            tty=spec.tty,
            stdin_open=spec.stdin_open,
            name=spec.name,
            network=spec.network,
            dns_search=spec.dns_search,
            volumes=spec.volumes,
            environment=spec.environment,
            ports=spec.ports,
        )

    def get(self, identifier: str):
        return docker_client.containers.get(identifier)

    def start(self, container):
        container.start()

    def stop(self, container):
        container.stop()

    def remove(self, container, force: bool = True):
        container.remove(force=force)

    def logs(self, container, tail: int = 200):
        return container.logs(tail=tail)


runtime = ContainerRuntime()
