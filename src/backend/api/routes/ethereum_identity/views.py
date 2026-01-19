from django.shortcuts import get_object_or_404
from api.lib.firefly.firefly import Firefly_cli
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
import json
import requests
from .serializers import (
    EthereumIdentitySerializer,
    EthereumIdentityCreateSerializer,
)
from api.models import (
    EthereumIdentity,
    Firefly,
    APISecretKey,
    ResourceSet,
    EthEnvironment,
    IdentityDeployment,
)
from api.utils.test_time import timeitwithname
from rest_framework.decorators import authentication_classes, permission_classes


class EthereumIdentityViewSet(viewsets.ViewSet):

    def _get_api_base(self, eth_environment: EthEnvironment) -> str:
        system_resource_set = eth_environment.resource_sets.filter(
            ethereum_sub_resource_set__org_type=1
        ).first()
        if not system_resource_set:
            raise Exception("System resource set not found")
        system_firefly = Firefly.objects.filter(resource_set=system_resource_set).first()
        if not system_firefly:
            raise Exception("System firefly not found")
        deployment = IdentityDeployment.objects.filter(
            eth_environment=eth_environment
        ).first()
        if deployment and deployment.api_address:
            return deployment.api_address
        api_name = deployment.api_name if deployment and deployment.api_name else "IdentityRegistry"
        return f"http://{system_firefly.core_url}/api/v1/namespaces/default/apis/{api_name}"

    def _ensure_org_registered(
        self, api_base: str, org_name: str, org_admin_address: str
    ) -> None:
        if not org_admin_address:
            raise Exception("org_admin_address is required")
        response = requests.post(
            f"{api_base}/invoke/createOrganization",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {"input": {"orgName": org_name, "orgAdmin": org_admin_address}}
            ),
            timeout=60,
        )
        if response.status_code not in [200, 202]:
            text = response.text or ""
            if "already exists" in text.lower():
                return
            raise Exception(f"createOrganization failed: {text[:500]}")

    def _sync_identity(self, identity: EthereumIdentity, firefly: Firefly) -> dict:
        deployment = IdentityDeployment.objects.filter(
            eth_environment=identity.eth_environment
        ).first()
        if not deployment or not deployment.contract_address:
            return {
                "status": "failed",
                "error": "Identity contract not deployed",
            }

        api_base = self._get_api_base(identity.eth_environment)
        print(f"[ethereum-identity] sync via firefly: {api_base}", flush=True)

        org_name = identity.membership.name
        self._ensure_org_registered(api_base, org_name, identity.address)
        payload = {
            "input": {
                "identityAddress": identity.address,
                "fireflyIdentityId": identity.firefly_identity_id or "",
                "orgName": org_name,
                "customKey": identity.membership.name,
            },
        }
        response = requests.post(
            f"{api_base}/invoke/registerIdentity",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60,
        )
        if response.status_code not in [200, 202]:
            text = response.text or ""
            if "already registered" in text.lower():
                return {"status": "already_registered"}
            return {
                "status": "failed",
                "error": text[:500],
            }
        return {"status": "ok", "result": response.json()}

    def list(self, request):
        eth_environment_id = request.query_params.get("eth_environment_id")
        membership_id = request.query_params.get("membership_id")

        if eth_environment_id:
            eth_environment = EthEnvironment.objects.get(id=eth_environment_id)
            if membership_id:
                # Filter by both environment and membership
                queryset = EthereumIdentity.objects.filter(
                    eth_environment=eth_environment,
                    membership_id=membership_id
                )
            else:
                # Get all resource sets for this environment and then find EthereumIdentities by membership
                resource_sets = eth_environment.resource_sets.all()
                queryset = EthereumIdentity.objects.filter(
                    membership__in=[rs.membership for rs in resource_sets]
                )
        elif membership_id:
            # Filter only by membership
            queryset = EthereumIdentity.objects.filter(membership_id=membership_id)
        else:
            return Response(
                {"error": "At least one of eth_environment_id or membership_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EthereumIdentitySerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = EthereumIdentityCreateSerializer(data=request.data)
        if serializer.is_valid():
            eth_environment_id = serializer.data["eth_environment_id"]
            membership_id = serializer.data.get("membership_id")
            eth_environment = EthEnvironment.objects.get(id=eth_environment_id)

            # Get resource sets for this environment and membership
            if membership_id:
                # Get resource sets for the specific membership
                resource_sets = eth_environment.resource_sets.filter(membership_id=membership_id)
            else:
                # Get all resource sets for this environment
                resource_sets = eth_environment.resource_sets.all()

            if not resource_sets.exists():
                return Response(
                    {"error": "No resource sets found for this Ethereum environment"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the resource set for the specific membership
            resource_set = resource_sets.first()

            # Find firefly for this resource set (each membership has its own firefly)
            target_firefly = resource_set.firefly.first()
            if target_firefly is None:
                return Response(
                    {"error": "firefly not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate Ethereum account if address or private key not provided
            address = serializer.data.get("address")
            private_key = serializer.data.get("private_key")

            if not address or not private_key:
                # Create new Ethereum account using Firefly CLI
                firefly_name = "cello_" + eth_environment.name.lower()
                ff_cli = Firefly_cli()
                account_info = ff_cli.create_account(firefly_name)

                if not address:
                    address = account_info["address"]
                if not private_key:
                    private_key = account_info["privateKey"]

                # Wait for account creation to be broadcast and confirmed
                import time
                time.sleep(4)

            # Register identity to Firefly (Ethereum identity registration)
            firefly_identity_id = target_firefly.register_eth_identity_to_firefly(serializer.data["name"], address)
            if not firefly_identity_id:
                return Response(
                    {"error": "register to firefly failed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ethereum_identity = EthereumIdentity(
                name=serializer.data["name"],
                address=address,
                private_key=private_key,
                firefly_identity_id=firefly_identity_id,
                eth_environment=eth_environment,
                membership=resource_set.membership,
            )
            ethereum_identity.save()
            sync_result = self._sync_identity(ethereum_identity, target_firefly)
            return Response(
                {
                    "id": ethereum_identity.id,
                    "address": address,
                    "private_key": private_key,
                    "sync_status": sync_result.get("status"),
                    "sync_error": sync_result.get("error"),
                },
                status=status.HTTP_201_CREATED,
            )

    def retrieve(self, request, pk=None):
        ethereum_identity = EthereumIdentity.objects.get(pk=pk)
        serializer = EthereumIdentitySerializer(ethereum_identity)
        return Response(serializer.data)

    def delete(self, request, pk=None):
        queryset = EthereumIdentity.objects.all()
        ethereum_identity = get_object_or_404(queryset, pk=pk)
        ethereum_identity.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk=None):
        queryset = EthereumIdentity.objects.all()
        ethereum_identity = get_object_or_404(queryset, pk=pk)
        serializer = EthereumIdentitySerializer(ethereum_identity, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=True, url_path="sync")
    def sync(self, request, pk=None):
        queryset = EthereumIdentity.objects.all()
        ethereum_identity = get_object_or_404(queryset, pk=pk)
        sync_result = self._sync_identity(ethereum_identity, None)
        if sync_result.get("status") == "failed":
            return Response(sync_result, status=status.HTTP_400_BAD_REQUEST)
        return Response(sync_result, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=False, url_path="sync_all")
    def sync_all(self, request):
        eth_environment_id = request.data.get("eth_environment_id") or request.query_params.get("eth_environment_id")
        membership_id = request.data.get("membership_id") or request.query_params.get("membership_id")

        queryset = EthereumIdentity.objects.all()
        if eth_environment_id:
            queryset = queryset.filter(eth_environment_id=eth_environment_id)
        if membership_id:
            queryset = queryset.filter(membership_id=membership_id)

        if not queryset.exists():
            return Response(
                {"message": "No ethereum identities found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        results = []
        success = 0
        failed = 0
        skipped = 0

        for identity in queryset:
            resource_set = ResourceSet.objects.filter(membership=identity.membership).first()
            firefly = resource_set.firefly.first() if resource_set else None
            if not firefly:
                results.append(
                    {
                        "id": str(identity.id),
                        "status": "failed",
                        "error": "firefly not found for membership",
                    }
                )
                failed += 1
                continue
            sync_result = self._sync_identity(identity, firefly)
            status_value = sync_result.get("status")
            if status_value in ("ok", "already_registered"):
                success += 1
            elif status_value == "failed":
                failed += 1
            else:
                skipped += 1
            results.append(
                {
                    "id": str(identity.id),
                    "status": status_value,
                    "error": sync_result.get("error"),
                }
            )

        return Response(
            {
                "total": len(results),
                "success": success,
                "failed": failed,
                "skipped": skipped,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
