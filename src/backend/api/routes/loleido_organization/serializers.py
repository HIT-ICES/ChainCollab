from rest_framework import serializers
from api.models import LoleidoOrganization, UserJoinOrgInvitation, Consortium


class ConsortiumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consortium
        fields = "__all__"


class LoleidoOrganizationSerializer(serializers.ModelSerializer):
    # consortiums = ConsortiumSerializer(many=True, read_only=True)
    consortiums = serializers.SerializerMethodField()

    class Meta:
        model = LoleidoOrganization
        fields = "__all__"

    def get_consortiums(self, obj):
        # 获取与该组织关联的所有独特的 Consortium 对象
        consortiums = Consortium.objects.filter(
            membership__loleido_organization=obj
        ).distinct()
        return ConsortiumSerializer(consortiums, many=True).data


class UserJoinOrgInvitionSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    loleido_organization = LoleidoOrganizationSerializer()
    invitor = serializers.SerializerMethodField()

    class Meta:
        model = UserJoinOrgInvitation
        # fields = "__all__"
        exclude = ["create_at"]

    def get_date(self, obj):
        return obj.create_at.strftime("%Y-%m-%d %H:%M")

    def get_loleido_organization(self, obj):
        return {
            "name": obj.loleido_organization.name,
            "id": obj.loleido_organization.id,
        }

    def get_invitor(self, obj):
        return {"username": obj.invitor.username, "id": obj.invitor.id}
