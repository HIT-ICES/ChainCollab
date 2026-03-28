from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.routes.translator.serializers import (
    TranslatorBpmnContentSerializer,
    TranslatorDmnContentSerializer,
    TranslatorGenerateSerializer,
)
from apps.core.services import NewTranslatorClient, NewTranslatorError


class TranslatorProxyViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="chaincode/generate")
    def generate(self, request, *args, **kwargs):
        serializer = TranslatorGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            generated = NewTranslatorClient().generate_artifacts(
                serializer.validated_data["bpmnContent"],
                target=serializer.validated_data.get("target") or "go",
                artifact_name=serializer.validated_data.get("artifact_name"),
            )
        except NewTranslatorError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "bpmnContent": generated.get("chaincodeContent", ""),
                "dslContent": generated.get("dslContent", ""),
                "ffiContent": generated.get("ffiContent", "{}"),
                "target": generated.get("target", "go"),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="chaincode/participants")
    def participants(self, request, *args, **kwargs):
        serializer = TranslatorBpmnContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = NewTranslatorClient().get_participants(serializer.validated_data["bpmnContent"])
        except NewTranslatorError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="chaincode/messages")
    def messages(self, request, *args, **kwargs):
        serializer = TranslatorBpmnContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = NewTranslatorClient().get_messages(serializer.validated_data["bpmnContent"])
        except NewTranslatorError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="chaincode/business-rules")
    def business_rules(self, request, *args, **kwargs):
        serializer = TranslatorBpmnContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = NewTranslatorClient().get_business_rules(
                serializer.validated_data["bpmnContent"]
            )
        except NewTranslatorError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="dmn/decisions")
    def decisions(self, request, *args, **kwargs):
        serializer = TranslatorDmnContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = NewTranslatorClient().get_decisions(serializer.validated_data["dmnContent"])
        except NewTranslatorError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data, status=status.HTTP_200_OK)
