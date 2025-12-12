from flask import Blueprint

from ..docker_client import docker_client
from ..utils import build_response

bp = Blueprint("network", __name__)


@bp.route("/networks", methods=["GET"])
def get_network():
    containers = {}
    for container in docker_client.containers.list():
        containers[container.id] = {
            "id": container.id,
            "short_id": container.short_id,
            "name": container.name,
            "status": container.status,
            "image": str(container.image),
            "attrs": container.attrs,
        }
    return build_response(containers, "success")
