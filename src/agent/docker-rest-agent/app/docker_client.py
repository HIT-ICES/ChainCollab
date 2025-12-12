import logging
from typing import Any

import docker

from .config import CONFIG


class _DevContainers:
    def list(self, *args: Any, **kwargs: Any):
        logging.debug("dev containers.list called with %s %s", args, kwargs)
        return []

    def run(self, *args: Any, **kwargs: Any):
        raise RuntimeError("Docker operations被禁用：当前处于 AGENT_DEV_MODE 模式")

    def get(self, identifier: str):
        raise docker.errors.NotFound(f"dev mode container '{identifier}' not found")


class _DevImages:
    def build(self, *args: Any, **kwargs: Any):
        raise RuntimeError("构建镜像在 AGENT_DEV_MODE 下不可用")


class _DevDockerClient:
    def __init__(self):
        self.containers = _DevContainers()
        self.images = _DevImages()


if CONFIG.dev_mode:
    logging.warning("AGENT_DEV_MODE 已启用：跳过 Docker 连接，所有容器操作将被短路")
    docker_client = _DevDockerClient()
else:
    docker_client = docker.DockerClient(base_url=CONFIG.docker_url)
