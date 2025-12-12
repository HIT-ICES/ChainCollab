from flask import Blueprint, request

from ..services import get_provisioner
from ..utils import (
    FAIL_CODE,
    ValidationError,
    build_response,
    describe_container,
    get_container_or_404,
)

bp = Blueprint("ipfs", __name__)


@bp.route("/ipfs/nodes", methods=["POST"])
def create_ipfs_node():
    provisioner = get_provisioner("ipfs-node")
    try:
        data = provisioner.provision(request.form)
        return build_response(data, "IPFS node created", status=201)
    except ValidationError:
        raise
    except Exception as exc:
        return build_response(msg=str(exc), code=FAIL_CODE, status=500)


@bp.route("/ipfs/nodes/<name>", methods=["GET"])
def ipfs_node_detail(name):
    container = get_container_or_404(name)
    data = describe_container(container)
    try:
        provisioner = get_provisioner("ipfs-node")
        data.update(provisioner.describe(container))
    except ValueError:
        pass
    return build_response(data, "ipfs node detail")
