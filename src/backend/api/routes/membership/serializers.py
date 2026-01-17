from rest_framework import serializers
from api.models import Membership

class MembershipSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="loleido_organization.name", read_only=True)
    join_date = serializers.SerializerMethodField()
    class Meta:
        model = Membership
        exclude = ["create_at"]
    
    def get_join_date(self, obj):
        return obj.create_at.strftime("%Y-%m-%d %H")