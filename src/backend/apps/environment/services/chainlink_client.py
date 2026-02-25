from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

DEFAULT_CHAINLINK_NODES = [
    {"name": "chainlink1", "url": "http://localhost:6688"},
    {"name": "chainlink2", "url": "http://localhost:6689"},
    {"name": "chainlink3", "url": "http://localhost:6691"},
    {"name": "chainlink4", "url": "http://localhost:6692"},
]


def resolve_chainlink_root(anchor_file: Path) -> Path:
    here = anchor_file.resolve()
    for parent in here.parents:
        if parent.name != "src":
            continue
        candidate = parent / "oracle" / "CHAINLINK"
        if candidate.exists():
            return candidate
    for parent in here.parents:
        candidate = parent / "oracle" / "CHAINLINK"
        if candidate.exists():
            return candidate
    return Path(os.environ.get("CHAINLINK_ROOT", "/home/logres/system/src/oracle/CHAINLINK"))


def resolve_chainlink_credentials(chainlink_root: Path) -> tuple[str, str]:
    email = os.environ.get("CHAINLINK_EMAIL")
    password = os.environ.get("CHAINLINK_PASSWORD")
    if email and password:
        return str(email), str(password)

    api_path = chainlink_root / "chainlink" / ".api"
    if api_path.exists():
        lines = [
            line.strip()
            for line in api_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        if len(lines) >= 2:
            return lines[0], lines[1]
    return "admin@chain.link", "change-me-strong"


def resolve_chainlink_nodes(
    logger: logging.Logger | None = None,
    default_nodes: list[dict] | None = None,
) -> list[dict]:
    default_nodes = default_nodes or DEFAULT_CHAINLINK_NODES
    override = os.environ.get("CHAINLINK_NODES")
    if not override:
        return default_nodes
    override = override.strip()
    if not override:
        return default_nodes

    try:
        parsed = json.loads(override)
        if isinstance(parsed, list):
            nodes = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                url = str(item.get("url") or "").strip()
                if name and url:
                    nodes.append({"name": name, "url": url})
            if nodes:
                return nodes
    except Exception as exc:
        if logger:
            logger.warning("Failed to parse CHAINLINK_NODES as JSON: %s", exc)

    nodes = []
    for seg in override.split(","):
        seg = seg.strip()
        if not seg or "=" not in seg:
            continue
        name, url = seg.split("=", 1)
        name = name.strip()
        url = url.strip()
        if name and url:
            nodes.append({"name": name, "url": url})
    return nodes or default_nodes


def get_chainlink_node(nodes: list[dict], node_name: str | None) -> dict | None:
    if not node_name:
        return None
    for node in nodes:
        if node["name"] == node_name:
            return node
    return None


def auth_session(
    node_url: str,
    *,
    email: str,
    password: str,
    timeout: int = 10,
) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{node_url}/sessions",
        json={"email": email, "password": password},
        timeout=timeout,
    )
    response.raise_for_status()
    return session
