from rest_framework import serializers
from apps.core.models import Consortium, LoleidoOrgJoinConsortiumInvitation
from apps.core.routes.loleido_organization.serializers import (
    LoleidoOrganizationSerializer,
)



class ConsortiumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consortium
        fields = "__all__"

class LoliedoOrgJoinConsortiumInvitionSerializer(serializers.ModelSerializer):
    date =  serializers.SerializerMethodField()
    loleido_organization = serializers.SerializerMethodField()
    consortium = serializers.SerializerMethodField()
    invitor = serializers.SerializerMethodField()
    class Meta:
        model = LoleidoOrgJoinConsortiumInvitation
        # fields = "__all__"
        exclude = ['create_at']
        
    
    def get_date(self,obj):
        return obj.create_at.strftime("%Y-%m-%d %H:%M")
    def get_loleido_organization(self,obj):
        return {
            "id": obj.loleido_organization.id,
            "name": obj.loleido_organization.name,
        }
    def get_consortium(self,obj):
        return {
            "id": obj.consortium.id,
            "name": obj.consortium.name,
        }
    
    def get_invitor(self,obj):
        return {
            "id": obj.invitor.id,
            "name": obj.invitor.name,
        }
