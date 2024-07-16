from api.models import BPMN, BPMNInstance, BpmnParticipantBindingRecord
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


class BpmnSerializer(serializers.ModelSerializer):
    class Meta:
        model = BPMN
        fields = "__all__"


class BpmnInstanceSerializer(serializers.ModelSerializer):
    environment_name = serializers.SerializerMethodField()
    environment_id = serializers.SerializerMethodField()

    class Meta:
        model = BPMNInstance
        # exclude = ("environment",)
        fields = "__all__"
        # depth = 1

    def get_environment_name(self, obj):
        return obj.environment.name

    def get_environment_id(self, obj):
        return obj.environment.id


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


class BpmnBindingRecordSerializer(serializers.ModelSerializer):
    membership_name = serializers.CharField(source="membership.name")

    class Meta:
        model = BpmnParticipantBindingRecord
        fields = "__all__"
