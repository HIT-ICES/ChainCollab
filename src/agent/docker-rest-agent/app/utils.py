import ast
import json
import os
from typing import Any, Dict, Optional

from flask import abort, jsonify
import docker

from .docker_client import docker_client


PASS_CODE = "OK"
FAIL_CODE = "Fail"


class ValidationError(ValueError):
    """Raised when request data is invalid."""


def build_response(
    data: Optional[Dict[str, Any]] = None,
    msg: str = "",
    code: str = PASS_CODE,
    status: int = 200,
):
    return jsonify({"res": {"code": code, "data": data or {}, "msg": msg}}), status


def register_error_handlers(app):
    app.register_error_handler(
        ValidationError,
        lambda err: build_response(msg=str(err), code=FAIL_CODE, status=400),
    )


def require_param(form, field: str) -> str:
    value = form.get(field)
    if value in (None, "", []):
        raise ValidationError(f"'{field}' is required")
    return value


def parse_port_map(raw: Optional[str]) -> Dict[str, int]:
    if not raw:
        return {}
    try:
        if raw.strip().startswith("{"):
            return {str(k): int(v) for k, v in json.loads(raw).items()}
        return {str(k): int(v) for k, v in ast.literal_eval(raw).items()}
    except (ValueError, SyntaxError, AttributeError):
        raise ValidationError("port_map must be a valid JSON/object literal")


def get_container_or_404(identifier: str):
    try:
        return docker_client.containers.get(identifier)
    except docker.errors.NotFound:
        abort(404, description=f"container '{identifier}' not found")


def describe_container(container):
    container.reload()
    return {
        "id": container.id,
        "name": container.name,
        "status": container.status,
        "image": str(container.image),
        "ports": container.attrs.get("NetworkSettings", {}).get("Ports"),
    }
