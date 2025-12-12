import logging

from flask import Blueprint, request

from ..services import get_provisioner
from ..utils import (
    FAIL_CODE,
    ValidationError,
    build_response,
    describe_container,
    get_container_or_404,
)

bp = Blueprint("eth", __name__)


@bp.route("/ethnode", methods=["POST"])
def create_eth_node():
    provisioner = get_provisioner("eth-node")
    try:
        data = provisioner.provision(request.form)
        return build_response(data, "Ethereum node created successfully", status=201)
    except ValidationError:
        raise
    except Exception as e:
        logging.exception("Failed to launch Ethereum node %s", request.form.get("name"))
        return build_response(
            msg=f"Failed to create ethereum node: {str(e)}",
            code=FAIL_CODE,
            status=500,
        )


@bp.route("/ethnode/<name>", methods=["GET"])
def eth_node_detail(name):
    container = get_container_or_404(name)
    data = describe_container(container)
    try:
        provisioner = get_provisioner("eth-node")
        data.update(provisioner.describe(container))
    except ValueError:
        pass
    return build_response(data, "eth node detail")
