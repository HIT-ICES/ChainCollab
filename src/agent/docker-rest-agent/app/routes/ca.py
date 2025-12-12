import logging
import os
import time

from flask import Blueprint, request, send_file

from ..config import CA_SERVERS_PATH
from ..services import get_provisioner
from ..utils import (
    FAIL_CODE,
    ValidationError,
    build_response,
    describe_container,
    get_container_or_404,
)

bp = Blueprint("ca", __name__)


@bp.route("/ca", methods=["POST"])
def create_ca():
    provisioner = get_provisioner("fabric-ca")
    try:
        data = provisioner.provision(request.form)
        return build_response(data, "create ca success", status=201)
    except ValidationError:
        raise
    except Exception as exc:
        logging.exception("failed to create CA")
        return build_response(msg=str(exc), code=FAIL_CODE, status=500)


@bp.route("/ca/<ca_name>/operation", methods=["POST"])
def ca_operation(ca_name):
    command = request.form.get("action")

    if command == "start":
        try:
            container = get_container_or_404(ca_name)
            container.start()
            time.sleep(2)
            max_attempts = 30
            for _ in range(max_attempts):
                container.reload()
                if container.status == "running":
                    ca_server_home = os.path.join(CA_SERVERS_PATH, ca_name)
                    file_path = os.path.join(ca_server_home, "ca-cert.pem")

                    if os.path.isfile(file_path):
                        file_response = send_file(file_path, as_attachment=True)
                        file_response.status_code = 200
                        return file_response
                    return build_response(
                        msg="start ca success but ca_cert missing",
                        code=FAIL_CODE,
                        status=500,
                    )
                time.sleep(1)
        except Exception as exc:
            logging.exception("start ca failed for %s", ca_name)
            return build_response(
                msg=f"start ca failed: {exc}", code=FAIL_CODE, status=500
            )

        return build_response(msg="start ca success")

    elif command == "stop":
        try:
            container = get_container_or_404(ca_name)
            container.stop()
        except Exception as exc:
            logging.exception("stop ca failed for %s", ca_name)
            return build_response(
                msg=f"stop ca failed: {exc}", code=FAIL_CODE, status=500
            )

        return build_response(msg="stop ca success")
    else:
        raise ValidationError("unsupported action for CA")


@bp.route("/ca/<ca_name>", methods=["GET"])
def ca_detail(ca_name):
    try:
        container = get_container_or_404(ca_name)
        data = describe_container(container)
        provisioner = get_provisioner("fabric-ca")
        data.update(provisioner.describe(container))
        return build_response(data, "ca detail")
    except Exception as exc:
        logging.exception("fetch ca detail failed for %s", ca_name)
        return build_response(
            msg=f"failed to fetch ca detail: {exc}", code=FAIL_CODE, status=500
        )
