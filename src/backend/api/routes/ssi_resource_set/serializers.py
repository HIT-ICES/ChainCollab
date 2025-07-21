from rest_framework import serializers
from api.models import SSIResourceSet, SSIAgentNode

class SSIResourceSetSerializer(serializers.ModelSerializer):
    SSI_agent_node = serializers.PrimaryKeyRelatedField(
        queryset=SSIAgentNode.objects.all(),
        required=False,
        allow_null=True,
        help_text="ID of the linked SSI Agent Node"
    )

    class Meta:
        model = SSIResourceSet
        fields = "__all__"
        read_only_fields = ("id", "created_at")
        
    # def create(self, validated_data):
    #     return SSIResourceSet.objects.create(**validated_data)