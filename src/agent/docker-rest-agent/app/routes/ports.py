from flask import Blueprint, request

from ..infrastructure.ports import get_available_ports
from ..utils import ValidationError, build_response

bp = Blueprint("ports", __name__)


@bp.route("/ports", methods=["GET"])
def port_probe():
    port_number = request.args.get("port_number")
    if port_number is None:
        raise ValidationError("port_number is required")
    try:
        port_number = int(port_number)
    except ValueError:
        raise ValidationError("port_number should be a number")

    available_ports = get_available_ports(port_number)
    return build_response(available_ports, "success")
