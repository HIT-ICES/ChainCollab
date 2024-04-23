from rest_framework import serializers
from api.models import APISecretKey

class APISecretKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APISecretKey
        fields = "__all__"

class APISecretKeyCreateSerializer(serializers.Serializer):
    environment_id = serializers.CharField(max_length=100)
    membership_id = serializers.CharField(max_length=100)

class APISecretKeyCreateResponceSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=100)
    secret = serializers.CharField(max_length=100)