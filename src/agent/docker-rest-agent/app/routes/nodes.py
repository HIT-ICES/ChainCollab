import logging

from flask import Blueprint, request

from ..services import get_provisioner
from ..utils import (
    FAIL_CODE,
    ValidationError,
    build_response,
    describe_container,
    get_container_or_404,
    require_param,
)

bp = Blueprint("nodes", __name__)


def resolve_node_type(form_data):
    explicit_type = form_data.get("node_type")
    if explicit_type:
        return explicit_type
    legacy_type = form_data.get("type", "peer")
    if legacy_type == "peer":
        return "fabric-peer"
    if legacy_type == "orderer":
        return "fabric-orderer"
    return legacy_type


@bp.route("/nodes", methods=["POST"])
def create_node():
    node_type = resolve_node_type(request.form)
    try:
        provisioner = get_provisioner(node_type)
    except ValueError as exc:
        raise ValidationError(str(exc))
    try:
        data = provisioner.provision(request.form)
    except ValidationError:
        raise
    except Exception as exc:
        logging.exception("failed to create node %s", request.form.get("name"))
        return build_response(
            msg=f"creation failed: {exc}", code=FAIL_CODE, status=500
        )
    data["node_type"] = node_type
    return build_response(data, "node created")


@bp.route("/nodes/<id>", methods=["GET", "POST"])
def operate_node(id):
    container = get_container_or_404(id)
    if request.method == "POST":
        act = request.form.get("action")
        try:
            if act == "start":
                container.start()
                msg = "node started"
            elif act == "restart":
                container.restart()
                msg = "node restarted"
            elif act == "stop":
                container.stop()
                msg = "node stopped"
            elif act == "delete":
                container.remove()
                msg = "node deleted"
            elif act == "update":
                cmd = require_param(request.form, "cmd")
                env = {}
                if "msp" in request.form:
                    env["HLF_NODE_MSP"] = request.form.get("msp")
                if "tls" in request.form:
                    env["HLF_NODE_TLS"] = request.form.get("tls")
                if "bootstrap_block" in request.form:
                    env["HLF_NODE_BOOTSTRAP_BLOCK"] = request.form.get("bootstrap_block")
                if "peer_config_file" in request.form:
                    env["HLF_NODE_PEER_CONFIG"] = request.form.get("peer_config_file")
                if "orderer_config_file" in request.form:
                    env["HLF_NODE_ORDERER_CONFIG"] = request.form.get("orderer_config_file")
                container.exec_run(
                    cmd,
                    detach=True,
                    tty=True,
                    stdin=True,
                    environment=env,
                )
                container.restart()
                msg = "node updated"
            else:
                raise ValidationError("undefined action")
        except ValidationError:
            raise
        except Exception as exc:
            logging.exception("failed to %s node %s", act, id)
            return build_response(
                msg=f"{act} failed: {exc}", code=FAIL_CODE, status=500
            )
        return build_response({"id": container.id, "status": container.status}, msg)

    node_type = request.args.get("node_type")
    data = describe_container(container)
    if node_type:
        try:
            provisioner = get_provisioner(node_type)
            data.update(provisioner.describe(container))
        except ValueError:
            pass
    return build_response(data, "node detail")


@bp.route("/nodes/<id>/logs", methods=["GET"])
def node_logs(id):
    tail = request.args.get("tail", 200)
    try:
        tail = int(tail)
    except ValueError:
        raise ValidationError("tail must be an integer")
    container = get_container_or_404(id)
    logs = container.logs(tail=tail).decode("utf-8", errors="ignore")
    return build_response({"id": container.id, "logs": logs}, "node logs")
