from rest_framework import serializers


class TranslatorGenerateSerializer(serializers.Serializer):
    bpmnContent = serializers.CharField()
    target = serializers.ChoiceField(choices=("go", "solidity"), required=False)
    artifact_name = serializers.CharField(required=False, allow_blank=True)


class TranslatorBpmnContentSerializer(serializers.Serializer):
    bpmnContent = serializers.CharField()


class TranslatorDmnContentSerializer(serializers.Serializer):
    dmnContent = serializers.CharField()
