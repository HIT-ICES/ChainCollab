import json
import logging
from typing import Optional

from common.utils.http_client import post_json

LOG = logging.getLogger(__name__)


def register_identity(core_url: str, name: str, key: str, parent: str) -> Optional[str]:
    api_address = f"http://{core_url}/api/v1/identities?confirm=true"
    payload = {"parent": parent, "key": key, "name": name}

    LOG.info("[FF] action=register_identity core=%s parent=%s name=%s", core_url, parent, name)
    LOG.debug("[FF] action=register_identity payload=%s", json.dumps({**payload, "key": "***"}))

    try:
        status_code, response_json = post_json(
            api_address,
            body=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
            expected_status=(200, 201, 202),
        )
        LOG.info("[FF] action=register_identity status=%s", status_code)
        LOG.debug(
            "[FF] action=register_identity body=%s",
            json.dumps(response_json, ensure_ascii=False),
        )
    except Exception:
        LOG.exception("[FF] action=register_identity failed core=%s name=%s", core_url, name)
        return None

    return response_json.get("id")
