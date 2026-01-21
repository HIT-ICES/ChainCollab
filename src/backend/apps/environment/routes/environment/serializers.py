from rest_framework import serializers
from apps.environment.models import Environment, EthEnvironment

class EnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Environment
        fields = "__all__"
        
class EthEnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EthEnvironment
        fields = "__all__"
