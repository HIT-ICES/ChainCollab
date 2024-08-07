from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status


from api.models import (
    FabricIdentity,
    Node,
    ResourceSet,
    Membership,
    Firefly,
    FabricResourceSet,
)
from api.common.enums import FabricCAOrgType, FabricNodeType


class SearchView(viewsets.ViewSet):

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
                membership_id=mem.id, environment_id=env_id
            )
            resource_set = ResourceSet.objects.filter(
                environment_id=env_id, membership_id=mem.id
            )
            if resource_set.exists():
                firefly = Firefly.objects.get(resource_set_id=resource_set[0].id)
                core_url = firefly.core_url
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
                                "name": identity.name,
                                "firefly_identity_id": identity.firefly_identity_id,
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
