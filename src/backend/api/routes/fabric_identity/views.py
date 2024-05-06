from django.shortcuts import get_object_or_404
from requests import get, post
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import FabricIdentitySerializer, GatewayRegisterSerializer, FabricIdentityCreateSerializer
from api.models import FabricIdentity, Firefly, APISecretKey, ResourceSet
from api.config import DEFAULT_AGENT, DEFAULT_CHANNEL_NAME, FABRIC_CONFIG
from api.utils.test_time import timeitwithname
from rest_framework.decorators import authentication_classes, permission_classes


class FabricIdentityViewSet(viewsets.ViewSet):

    # platform method
    def list(self, request):
        queryset = FabricIdentity.objects.all()
        serializer = FabricIdentitySerializer(queryset, many=True)
        return Response(serializer.data)

    # platform method
    def create(self, request):
        
        serializer = FabricIdentityCreateSerializer(data=request.data)
        if serializer.is_valid():
            resource_set_id = serializer.data["resource_set_id"]
            resource_set = ResourceSet.objects.get(id=resource_set_id)
            
            # register
            target_firefly = resource_set.firefly.get()
            if target_firefly is None:
                return Response(
                    {"error": "firefly not found"}, status=status.HTTP_400_BAD_REQUEST
                )
            name, secret = target_firefly.register_certificate(
                name=serializer.data["name_of_identity"],
                attributes=serializer.data["attributes"],
            )
            success = target_firefly.enroll_certificate(name, secret, serializer.data["attributes"])
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
                name=serializer.data["name_of_fabric_identity"],
                signer=serializer.data["name_of_identity"],
                secret=serializer.data["secret_of_identity"],
                environment=resource_set.environment,
                membership=resource_set.membership,
            )
            fabric_identity.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        queryset = FabricIdentity.objects.all()
        fabric_identity = get_object_or_404(queryset, pk=pk)
        serializer = FabricIdentitySerializer(fabric_identity)
        return Response(serializer.data)

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
                membership=api_secret_key.membership, environment=api_secret_key.environment
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
            success = target_firefly.enroll_certificate(name, secret, serializer.data["attributes"])
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
                name=serializer.data["name_of_fabric_identity"],
                signer=serializer.data["name_of_identity"],
                secret=serializer.data["secret_of_identity"],
                environment = api_secret_key.environment,
                membership = api_secret_key.membership,
            )
            fabric_identity.save()
            return Response(
                {"id": fabric_identity.id, "secret": secret}, status=status.HTTP_201_CREATED
            )