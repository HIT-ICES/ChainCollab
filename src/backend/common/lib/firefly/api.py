import json
import logging
import os
from typing import Optional

import requests

LOG = logging.getLogger(__name__)


def register_identity(core_url: str, name: str, key: str, parent: str) -> Optional[str]:
    api_address = f"http://{core_url}/api/v1/identities?confirm=true"
    payload = {"parent": parent, "key": key, "name": name}
    timeout = int(os.environ.get("FIREFLY_IDENTITY_CONFIRM_TIMEOUT_SECONDS", "180"))

    LOG.info(
        "[FF] action=register_identity core=%s parent=%s name=%s timeout=%ss",
        core_url,
        parent,
        name,
        timeout,
    )
    LOG.debug("[FF] action=register_identity payload=%s", json.dumps({**payload, "key": "***"}))

    try:
        response = requests.post(
            api_address,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        status_code = response.status_code
        try:
            response_json = response.json()
        except Exception:
            response_json = response.text
        if status_code not in (200, 201, 202):
            raise RuntimeError(
                f"HTTP POST {api_address} failed with status {status_code}: {response_json}"
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
