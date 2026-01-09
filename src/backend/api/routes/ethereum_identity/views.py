from django.shortcuts import get_object_or_404
from api.lib.firefly.firefly import Firefly_cli
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import (
    EthereumIdentitySerializer,
    EthereumIdentityCreateSerializer,
)
from api.models import EthereumIdentity, Firefly, APISecretKey, ResourceSet, EthEnvironment
from api.utils.test_time import timeitwithname
from rest_framework.decorators import authentication_classes, permission_classes


class EthereumIdentityViewSet(viewsets.ViewSet):

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
                time.sleep(2)

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
            return Response(
                {
                    "id": ethereum_identity.id,
                    "address": address,
                    "private_key": private_key
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