from django.shortcuts import get_object_or_404
from requests import get, post
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import (
    APISecretKeySerializer,
    APISecretKeyCreateSerializer,
    APISecretKeyCreateResponceSerializer,
)
from api.models import FabricIdentity, Firefly, APISecretKey, ResourceSet
from api.config import DEFAULT_AGENT, DEFAULT_CHANNEL_NAME, FABRIC_CONFIG
from api.utils.test_time import timeitwithname
from rest_framework.decorators import authentication_classes, permission_classes


class APISecretKeyViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = APISecretKey.objects.all()
        serializer = APISecretKeySerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = APISecretKeyCreateSerializer(data=request.data)
        user = request.user

        environment_id = request.data.get("environment_id", None)
        membership_id = request.data.get("membership_id", None)
        if not environment_id or not membership_id:
            return Response(
                {"error": "environment_id and membership_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # generate random key
        import random
        import string

        key = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        secret = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        if serializer.is_valid():
            api_secret_key = APISecretKey.objects.create(
                user=user,
                key=key,
                key_secret=secret,
                environment_id=environment_id,
                membership_id=membership_id,
            )
            # api_secret_key.save()
            return Response(
                {"key": key, "secret": secret}, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        queryset = APISecretKey.objects.all()
        api_secret_key = get_object_or_404(queryset, pk=pk)
        serializer = APISecretKeySerializer(api_secret_key)
        return Response(serializer.data)

    def delete(self, request, pk=None):
        queryset = APISecretKey.objects.all()
        api_secret_key = get_object_or_404(queryset, pk=pk)
        api_secret_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk=None):
        queryset = APISecretKey.objects.all()
        api_secret_key = get_object_or_404(queryset, pk=pk)
        serializer = APISecretKeySerializer(api_secret_key, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
