from rest_framework import serializers
from api.models import Membership, SSIAgentNode

class MembershipSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="loleido_organization.name", read_only=True)
    join_date = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField() 
    class Meta:
        model = Membership
        exclude = ["create_at"]
    
    def get_join_date(self, obj):
        return obj.create_at.strftime("%Y-%m-%d %H")
    
    def get_status(self, obj):
        try:
            ssi_agent_node = SSIAgentNode.objects.filter(membership=obj).first()
            if ssi_agent_node:
                return ssi_agent_node.status
            else:
                return None
        except SSIAgentNode.DoesNotExist:
            return "Not Available"