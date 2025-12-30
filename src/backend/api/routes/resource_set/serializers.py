from rest_framework import serializers
from api.models import ResourceSet

class ResourceSetSerializer(serializers.ModelSerializer):
    membership_name = serializers.CharField(source="membership.name")
    membership_id = serializers.CharField(source="membership.id")
    org_type = serializers.SerializerMethodField()  # 应该是SerializerMethodField而不是MethodField
    org_id = serializers.CharField(source="membership.loleido_organization.id")
    msp = serializers.SerializerMethodField()


    class Meta:
        model = ResourceSet
        fields = "__all__"

    def get_org_type(self, obj):
        sub_resource_set = obj.sub_resource_set
        return "system_type" if  sub_resource_set.org_type == '1' else "user_type"

    def get_msp(self, obj):
        try:
            sub_resource_set = obj.sub_resource_set
            return sub_resource_set.msp
        except:
            return None

