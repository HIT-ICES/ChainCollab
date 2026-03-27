from pathlib import Path

import requests
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.environment.models import EthEnvironment
from apps.environment.services.chainlink_client import (
    DEFAULT_CHAINLINK_NODES,
    auth_session as chainlink_auth_session,
    get_chainlink_node,
    resolve_chainlink_credentials,
    resolve_chainlink_nodes,
    resolve_chainlink_root,
)


class ChainlinkJobViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    DEFAULT_NODES = DEFAULT_CHAINLINK_NODES

    def _resolve_credentials(self) -> tuple[str, str]:
        chainlink_root = resolve_chainlink_root(Path(__file__))
        return resolve_chainlink_credentials(chainlink_root)

    def _resolve_nodes(self) -> list[dict]:
        return resolve_chainlink_nodes(default_nodes=self.DEFAULT_NODES)

    def _get_node(self, node_name: str | None):
        return get_chainlink_node(self._resolve_nodes(), node_name)

    def _get_env(self, environment_id: str) -> EthEnvironment:
        return EthEnvironment.objects.get(pk=environment_id)

    def _ensure_env_ready(self, env: EthEnvironment):
        if env.status not in ["ACTIVATED", "STARTED"]:
            raise RuntimeError("Environment has not been activated or has started")
        if env.chainlink_status != "STARTED":
            raise RuntimeError("Chainlink cluster has not been started")

    def _ready_env_or_response(self, environment_id: str):
        try:
            env = self._get_env(environment_id)
            self._ensure_env_ready(env)
            return env, None
        except EthEnvironment.DoesNotExist:
            return None, Response(status=status.HTTP_404_NOT_FOUND)
        except RuntimeError as exc:
            return None, Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def _auth_session(self, node_url: str) -> requests.Session:
        email, password = self._resolve_credentials()
        return chainlink_auth_session(node_url, email=email, password=password, timeout=10)

    def _node_query(self, request):
        return (
            request.query_params.get("node")
            or request.data.get("node")
            or request.data.get("node_name")
        )

    def list(self, request, environment_id=None, *args, **kwargs):
        _, error_response = self._ready_env_or_response(environment_id)
        if error_response:
            return error_response

        node_name = self._node_query(request)
        nodes = self._resolve_nodes()
        if node_name:
            node = self._get_node(node_name)
            if not node:
                return Response(
                    {"message": f"Unknown chainlink node: {node_name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            nodes = [node]

        items = []
        errors = []
        for node in nodes:
            try:
                session = self._auth_session(node["url"])
                resp = session.get(f"{node['url']}/v2/jobs", timeout=12)
                resp.raise_for_status()
                data = resp.json().get("data") or []
                for job in data:
                    attrs = job.get("attributes") or {}
                    items.append(
                        {
                            "node": node["name"],
                            "node_url": node["url"],
                            "id": job.get("id"),
                            "type": job.get("type"),
                            "name": attrs.get("name"),
                            "externalJobID": attrs.get("externalJobID"),
                            "schemaVersion": attrs.get("schemaVersion"),
                            "createdAt": attrs.get("createdAt"),
                            "maxTaskDuration": attrs.get("maxTaskDuration"),
                            "raw": job,
                        }
                    )
            except Exception as exc:
                errors.append({"node": node["name"], "error": str(exc)})

        return Response({"items": items, "errors": errors}, status=status.HTTP_200_OK)

    def create(self, request, environment_id=None, *args, **kwargs):
        _, error_response = self._ready_env_or_response(environment_id)
        if error_response:
            return error_response

        toml = request.data.get("toml")
        if not isinstance(toml, str) or not toml.strip():
            return Response({"message": "toml is required"}, status=status.HTTP_400_BAD_REQUEST)

        node_name = self._node_query(request)
        all_nodes = bool(request.data.get("all_nodes"))
        nodes = self._resolve_nodes()
        if node_name and not all_nodes:
            node = self._get_node(node_name)
            if not node:
                return Response(
                    {"message": f"Unknown chainlink node: {node_name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            nodes = [node]
        elif not all_nodes:
            nodes = [nodes[0]]

        created = []
        errors = []
        for node in nodes:
            try:
                session = self._auth_session(node["url"])
                resp = session.post(
                    f"{node['url']}/v2/jobs",
                    json={"toml": toml},
                    timeout=20,
                )
                resp.raise_for_status()
                payload = resp.json().get("data") or {}
                attrs = payload.get("attributes") or {}
                created.append(
                    {
                        "node": node["name"],
                        "node_url": node["url"],
                        "id": payload.get("id"),
                        "name": attrs.get("name"),
                        "externalJobID": attrs.get("externalJobID"),
                        "raw": payload,
                    }
                )
            except Exception as exc:
                errors.append({"node": node["name"], "error": str(exc)})

        if created and not errors:
            return Response({"items": created}, status=status.HTTP_201_CREATED)
        if created and errors:
            return Response({"items": created, "errors": errors}, status=status.HTTP_207_MULTI_STATUS)
        return Response({"message": "Create job failed", "errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, environment_id=None, *args, **kwargs):
        _, error_response = self._ready_env_or_response(environment_id)
        if error_response:
            return error_response

        node_name = self._node_query(request)
        node = self._get_node(node_name)
        if not node:
            return Response(
                {"message": "node is required, e.g. chainlink1"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = self._auth_session(node["url"])
            resp = session.get(f"{node['url']}/v2/jobs/{pk}", timeout=12)
            resp.raise_for_status()
            return Response(
                {"node": node["name"], "node_url": node["url"], "item": resp.json().get("data")},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None, environment_id=None, *args, **kwargs):
        _, error_response = self._ready_env_or_response(environment_id)
        if error_response:
            return error_response

        node_name = self._node_query(request)
        node = self._get_node(node_name)
        if not node:
            return Response(
                {"message": "node is required, e.g. chainlink1"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = self._auth_session(node["url"])
            resp = session.delete(f"{node['url']}/v2/jobs/{pk}", timeout=12)
            if resp.status_code not in [200, 202, 204]:
                resp.raise_for_status()
            return Response({"node": node["name"], "id": pk, "deleted": True}, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, environment_id=None, *args, **kwargs):
        return self._replace_job(request, pk, environment_id)

    def partial_update(self, request, pk=None, environment_id=None, *args, **kwargs):
        return self._replace_job(request, pk, environment_id)

    def _replace_job(self, request, pk, environment_id):
        _, error_response = self._ready_env_or_response(environment_id)
        if error_response:
            return error_response

        node_name = self._node_query(request)
        node = self._get_node(node_name)
        if not node:
            return Response(
                {"message": "node is required, e.g. chainlink1"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        toml = request.data.get("toml")
        if not isinstance(toml, str) or not toml.strip():
            return Response({"message": "toml is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = self._auth_session(node["url"])
            delete_resp = session.delete(f"{node['url']}/v2/jobs/{pk}", timeout=12)
            if delete_resp.status_code not in [200, 202, 204, 404]:
                delete_resp.raise_for_status()
            create_resp = session.post(
                f"{node['url']}/v2/jobs",
                json={"toml": toml},
                timeout=20,
            )
            create_resp.raise_for_status()
            return Response(
                {
                    "node": node["name"],
                    "replaced_from": pk,
                    "item": create_resp.json().get("data"),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
