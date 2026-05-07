from django.shortcuts import get_object_or_404
from requests import get, post
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import (
    FabricIdentitySerializer,
    GatewayRegisterSerializer,
    FabricIdentityCreateSerializer,
)
from apps.infra.models import APISecretKey
from apps.infra.models import Firefly
from apps.fabric.models import FabricIdentity, ResourceSet
from apps.api.config import DEFAULT_AGENT, DEFAULT_CHANNEL_NAME, FABRIC_CONFIG
from common.utils.test_time import timeitwithname
from rest_framework.decorators import authentication_classes, permission_classes


class FabricIdentityViewSet(viewsets.ViewSet):
    def _resolve_firefly_identity_map(self, resource_set):
        target_firefly = resource_set.firefly.first()
        if target_firefly is None:
            return {}
        try:
            response = get(
                f"http://{target_firefly.core_url}/api/v1/identities",
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

    def _serialize_identity(self, identity, firefly_identity_id: str = ""):
        data = FabricIdentitySerializer(identity).data
        data["name"] = identity.name_of_fabric_identity or identity.name_of_identity or ""
        data["signer"] = identity.name_of_identity or ""
        data["membership"] = (
            str(identity.resource_set.membership_id)
            if identity.resource_set and identity.resource_set.membership_id
            else ""
        )
        data["environment"] = (
            str(identity.resource_set.environment_id)
            if identity.resource_set and identity.resource_set.environment_id
            else ""
        )
        data["firefly_identity_id"] = firefly_identity_id or ""
        return data

    # platform method
    def list(self, request):
        resource_set_id = request.query_params.get("resource_set_id")
        resource_set = get_object_or_404(ResourceSet, id=resource_set_id)
        queryset = FabricIdentity.objects.filter(resource_set=resource_set)
        firefly_identity_map = self._resolve_firefly_identity_map(resource_set)
        return Response(
            [
                self._serialize_identity(
                    identity,
                    firefly_identity_map.get(identity.name_of_identity, ""),
                )
                for identity in queryset
            ]
        )

    # platform method
    def create(self, request):

        serializer = FabricIdentityCreateSerializer(data=request.data)
        if serializer.is_valid():
            resource_set_id = serializer.validated_data["resource_set_id"]
            resource_set = get_object_or_404(ResourceSet, id=resource_set_id)

            # register
            target_firefly = resource_set.firefly.get()
            if target_firefly is None:
                return Response(
                    {"error": "firefly not found"}, status=status.HTTP_400_BAD_REQUEST
                )
            name, secret = target_firefly.register_certificate(
                name=serializer.validated_data["name_of_identity"],
                attributes=serializer.validated_data["attributes"],
            )
            success = target_firefly.enroll_certificate(
                name, secret, serializer.validated_data["attributes"]
            )
            if not success:
                return Response(
                    {"error": "enroll failed"}, status=status.HTTP_400_BAD_REQUEST
                )

            # register to firefly
            firefly_identity_id = target_firefly.register_to_firefly(name)
            if not firefly_identity_id:
                return Response(
                    {"error": "register to firefly failed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            fabric_identity = FabricIdentity(
                name_of_fabric_identity=serializer.validated_data["name_of_fabric_identity"],
                name_of_identity=serializer.validated_data["name_of_identity"],
                secret_of_identity=serializer.validated_data["secret_of_identity"],
                attributes=serializer.validated_data["attributes"],
                resource_set=resource_set,
            )
            fabric_identity.save()
            return Response(
                {"id": fabric_identity.id},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        fabric_identity = FabricIdentity.objects.get(pk=pk)
        firefly_identity_map = self._resolve_firefly_identity_map(
            fabric_identity.resource_set
        )
        return Response(
            self._serialize_identity(
                fabric_identity,
                firefly_identity_map.get(fabric_identity.name_of_identity, ""),
            )
        )

    def delete(self, request, pk=None):
        queryset = FabricIdentity.objects.all()
        fabric_identity = get_object_or_404(queryset, pk=pk)
        fabric_identity.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk=None):
        queryset = FabricIdentity.objects.all()
        fabric_identity = get_object_or_404(queryset, pk=pk)
        serializer = FabricIdentitySerializer(fabric_identity, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # API GATEWAY METHOD

    @authentication_classes([])  # 不需要认证
    @permission_classes([])  # 不需要权限验证
    @action(methods=["post"], detail=False)
    def create_fabric_identity(self, request):
        serializer = GatewayRegisterSerializer(data=request.data)
        if serializer.is_valid():
            # find APIKEY
            api_secret_key = APISecretKey.objects.filter(
                key=serializer.data["api_key"]
            ).first()
            if api_secret_key is None:
                return Response(
                    {"error": "api_key not found"}, status=status.HTTP_400_BAD_REQUEST
                )
            verified = api_secret_key.verifyKeySecret(serializer.data["secret_key"])
            if not verified:
                return Response(
                    {"error": "api_key or secret_key not match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # create fabric identity

            resource_set = ResourceSet.objects.filter(
                membership=api_secret_key.membership,
                environment=api_secret_key.environment,
            ).first()
            if resource_set is None:
                return Response(
                    {"error": "resource set not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            target_firefly = resource_set.firefly.get()
            if target_firefly is None:
                return Response(
                    {"error": "firefly not found"}, status=status.HTTP_400_BAD_REQUEST
                )
            name, secret = target_firefly.register_certificate(
                name=serializer.data["name_of_identity"],
                attributes=serializer.data["attributes"],
            )
            success = target_firefly.enroll_certificate(
                name, secret, serializer.data["attributes"]
            )
            if not success:
                return Response(
                    {"error": "enroll failed"}, status=status.HTTP_400_BAD_REQUEST
                )
            # register to firefly
            success = target_firefly.register_to_firefly(name)
            if not success:
                return Response(
                    {"error": "register to firefly failed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            fabric_identity = FabricIdentity(
                name_of_fabric_identity=serializer.data["name_of_fabric_identity"],
                name_of_identity=serializer.data["name_of_identity"],
                secret_of_identity=serializer.data["secret_of_identity"],
                attributes=serializer.data["attributes"],
                resource_set=resource_set,
            )
            fabric_identity.save()
            return Response(
                {"id": fabric_identity.id, "secret": secret},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
