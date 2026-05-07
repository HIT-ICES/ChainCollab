from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status


from apps.infra.models import Firefly
from apps.fabric.models import (
    FabricIdentity,
    Node,
    ResourceSet,
    FabricResourceSet,
)
from apps.core.models import Membership
from common.enums import FabricCAOrgType, FabricNodeType


class SearchView(viewsets.ViewSet):
    def _resolve_firefly_identity_map(self, firefly):
        try:
            response = get(
                f"http://{firefly.core_url}/api/v1/identities",
                params={"limit": 1000},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return {}
        if not isinstance(payload, list):
            return {}
        return {
            str(item.get("name")): str(item.get("id"))
            for item in payload
            if item.get("name") and item.get("id")
        }

    @action(detail=False, methods=["get"], url_path="search-identity-by-org-and-env")
    def searchIdentityByOrgAndEnv(self, request, *args, **kwargs):
        """
        search
        """
        org_id = request.query_params.get("org_id", "")
        env_id = request.query_params.get("env_id", "")
        if org_id == "" or env_id == "":
            return Response({"status": "error", "detail": "org_id or env_id is empty"})

        memberships = Membership.objects.filter(loleido_organization_id=org_id)
        # filter the resource_set Firefly URL

        res = []
        for mem in memberships:
            fabric_identity = FabricIdentity.objects.filter(
                resource_set__membership_id=mem.id,
                resource_set__environment_id=env_id,
            )
            resource_set = ResourceSet.objects.filter(
                environment_id=env_id, membership_id=mem.id
            )
            if resource_set.exists():
                firefly = Firefly.objects.get(resource_set_id=resource_set[0].id)
                core_url = firefly.core_url
                firefly_identity_map = self._resolve_firefly_identity_map(firefly)
                fabric_resource_set = FabricResourceSet.objects.get(
                    resource_set_id=resource_set[0].id
                )
                msp = fabric_resource_set.name
            else:
                continue

            if fabric_identity.exists():
                res.append(
                    {
                        "membership_id": mem.id,
                        "membership_name": mem.name,
                        "identities": [
                            {
                                "identity_id": identity.id,
                                "name": identity.name_of_fabric_identity,
                                "signer": identity.name_of_identity,
                                "firefly_identity_id": firefly_identity_map.get(
                                    identity.name_of_identity, ""
                                ),
                                "firefly_msp": msp,
                                "core_url": core_url,
                            }
                            for identity in fabric_identity
                        ],
                    }
                )

        return Response(status=status.HTTP_200_OK, data=res)

    @action(detail=False, methods=["get"], url_path="search-peers-membership")
    def searchPeersMembership(self, request, *args, **kwargs):
        """
        search
        """
        org_id = request.query_params.get("org_id", "")
        env_id = request.query_params.get("env_id", "")
        if org_id == "" or env_id == "":
            return Response({"status": "error", "detail": "org_id or env_id is empty"})

        memberships = Membership.objects.filter(loleido_organization_id=org_id)
        # filter the resource_set Firefly URL

        res = []
        for mem in memberships:
            resource_set = ResourceSet.objects.filter(
                environment_id=env_id,
                membership_id=mem.id,
                sub_resource_set__org_type=FabricCAOrgType.USERORG.value,
            )
            if resource_set.exists():
                fabric_resource_set = FabricResourceSet.objects.get(
                    resource_set_id=resource_set[0].id
                )
                peer_node = Node.objects.filter(
                    fabric_resource_set=fabric_resource_set,
                    type=FabricNodeType.Peer.name.lower(),
                )
            else:
                continue
            if peer_node.exists():
                res.append(
                    {
                        "membership_id": mem.id,
                        "peer_node": peer_node.get().id,
                        "membership_name": mem.name,
                    }
                )

        return Response(status=status.HTTP_200_OK, data=res)
