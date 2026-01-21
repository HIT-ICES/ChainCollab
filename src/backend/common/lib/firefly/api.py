import json
import logging
from typing import Optional

from requests import post

LOG = logging.getLogger(__name__)


def register_identity(core_url: str, name: str, key: str, parent: str) -> Optional[str]:
    api_address = f"http://{core_url}/api/v1/identities?confirm=true"
    payload = {"parent": parent, "key": key, "name": name}

    LOG.info("[FF] action=register_identity core=%s parent=%s name=%s", core_url, parent, name)
    LOG.debug("[FF] action=register_identity payload=%s", json.dumps({**payload, "key": "***"}))

    response = post(
        api_address,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    LOG.info("[FF] action=register_identity status=%s", response.status_code)
    LOG.debug("[FF] action=register_identity body=%s", response.text)

    try:
        response_json = response.json()
    except Exception:
        return None

    return response_json.get("id")
