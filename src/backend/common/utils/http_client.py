from __future__ import annotations

import json
import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOG = logging.getLogger(__name__)


def _session_with_retry() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_SESSION = _session_with_retry()


def request_json(
    method: str,
    url: str,
    *,
    timeout: int = 30,
    expected_status: set[int] | tuple[int, ...] = (200, 201, 202),
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    data_body: str | None = None,
) -> tuple[int, Any]:
    response = _SESSION.request(
        method=method.upper(),
        url=url,
        headers=headers,
        params=params,
        json=json_body,
        data=data_body,
        timeout=timeout,
    )
    status_code = response.status_code
    try:
        payload = response.json()
    except Exception:
        payload = response.text

    if status_code not in expected_status:
        snippet = payload
        if not isinstance(snippet, str):
            try:
                snippet = json.dumps(snippet, ensure_ascii=False)[:500]
            except Exception:
                snippet = str(snippet)[:500]
        raise RuntimeError(
            f"HTTP {method.upper()} {url} failed with status {status_code}: {snippet}"
        )
    return status_code, payload


def get_json(
    url: str,
    *,
    timeout: int = 30,
    expected_status=(200,),
    params: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    return request_json(
        "GET",
        url,
        timeout=timeout,
        expected_status=expected_status,
        params=params,
    )


def post_json(
    url: str,
    *,
    timeout: int = 30,
    expected_status: set[int] | tuple[int, ...] = (200, 201, 202),
    body: Any = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    return request_json(
        "POST",
        url,
        timeout=timeout,
        expected_status=expected_status,
        headers=headers,
        json_body=body,
    )
