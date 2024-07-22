from api.models import (
    BPMN,
    DMN,
    BPMNInstance,
    ChainCode,
    Consortium,
    Environment,
    LoleidoOrganization,
)
from rest_framework import serializers


class BpmnCreateBody(serializers.ModelSerializer):

    class Meta:
        model = BPMN
        field = ("consortium", "user", "status", "name")


class BpmnPageQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(help_text="Page of filter", default=1, min_value=1)
    per_page = serializers.IntegerField(
        default=10, help_text="Per Page of filter", min_value=1, max_value=100
    )

class ChaincodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChainCode
        fields = "__all__"

class BpmnSerializer(serializers.ModelSerializer):

    chaincode = ChaincodeSerializer()
    mark = serializers.SerializerMethodField()

    def get_mark(self,obj):
        return "Logres"

    class Meta:
        model = BPMN
        fields = "__all__"


class BpmnListSerializer(serializers.ModelSerializer):
    consortium_id = serializers.PrimaryKeyRelatedField(
        source="consortium", queryset=Consortium.objects.all(), allow_null=True
    )
    organization_id = serializers.PrimaryKeyRelatedField(
        source="organization", queryset=LoleidoOrganization.objects.all()
    )
    chaincode_id = serializers.PrimaryKeyRelatedField(
        source="chaincode", queryset=ChainCode.objects.all(), allow_null=True
    )
    environment_id = serializers.PrimaryKeyRelatedField(
        source="environment", queryset=Environment.objects.all(), allow_null=True
    )
    environment_name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = BPMN
        fields = [
            "id",
            "consortium_id",
            "organization_id",
            "organization_name",
            "status",
            "name",
            "participants",
            "events",
            "bpmnContent",
            "svgContent",
            "chaincode_id",
            "chaincode_content",
            "firefly_url",
            "ffiContent",
            "environment_id",
            "environment_name",
        ]

    def get_environment_name(self, obj):
        return obj.environment.name if obj.environment else None

    def get_organization_name(self, obj):
        return obj.organization.name


class DmnSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMN
        fields = "__all__"


class BpmnInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BPMNInstance
        # exclude = ("environment",)
        fields = "__all__"
        # depth = 1


class BpmnInstanceChaincodeSerializer(serializers.ModelSerializer):
    environment_name = serializers.SerializerMethodField()
    environment_id = serializers.SerializerMethodField()
    chaincode_id = serializers.SerializerMethodField()
    chaincode_name = serializers.SerializerMethodField()

    class Meta:
        model = BPMNInstance
        # exclude = ("environment",)
        fields = "__all__"
        # depth = 1

    def get_environment_name(self, obj):
        return obj.environment.name

    def get_environment_id(self, obj):
        return obj.environment.id

    def get_chaincode_id(self, obj):
        if obj.chaincode:
            return obj.chaincode.id
        return None

    def get_chaincode_name(self, obj):
        if obj.chaincode:
            return obj.chaincode.name
        return None
