# # serializers.py

# from rest_framework import serializers
# from api.models import AgentBinding

# class AgentBindingSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AgentBinding
#         fields = ['agent_url', 'public_did', 'label']

# class SSIInvitationSerializer(serializers.Serializer):
#     invitation_url = serializers.URLField()

# from api.models import ConnectionInvitation, DidConnection

# class ConnectionInvitationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ConnectionInvitation
#         fields = '__all__'

# class DidConnectionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DidConnection
#         fields = '__all__'

# from api.models import ConnectionRequest
# class ConnectionRequestSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ConnectionRequest
#         fields = '__all__'
