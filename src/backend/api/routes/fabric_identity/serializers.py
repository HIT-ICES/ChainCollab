from rest_framework import serializers
from api.models import FabricIdentity

class FabricIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricIdentity
        fields = "__all__"

class GatewayRegisterSerializer(serializers.Serializer):
    api_key = serializers.CharField(max_length=100)
    secret_key = serializers.CharField(max_length=100)
    name_of_fabric_identity = serializers.CharField(max_length=100) # data record name
    name_of_identity = serializers.CharField(max_length=100) # name of certicifate
    secret_of_identity = serializers.CharField(max_length=100)
    attributes = serializers.JSONField()
    
class FabricIdentityCreateSerializer(serializers.Serializer):
    resource_set_id = serializers.CharField(max_length=100)
    name_of_fabric_identity = serializers.CharField(max_length=100)
    name_of_identity = serializers.CharField(max_length=100)
    secret_of_identity = serializers.CharField(max_length=100)
    attributes = serializers.JSONField()