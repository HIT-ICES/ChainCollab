from rest_framework import serializers
from apps.ethereum.models import EthereumIdentity


class EthereumIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = EthereumIdentity
        fields = "__all__"


class EthereumIdentityCreateSerializer(serializers.Serializer):
    eth_environment_id = serializers.CharField(max_length=100)
    membership_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    name = serializers.CharField(max_length=100)
    address = serializers.CharField(max_length=100, required=False, allow_blank=True)
    private_key = serializers.CharField(max_length=200, required=False, allow_blank=True)
