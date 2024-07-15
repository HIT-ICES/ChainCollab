import logging
import os
import re
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from api.routes.bpmn.serializers import (
    BpmnBindingRecordSerializer,
    BpmnInstanceChaincodeSerializer,
    BpmnSerializer,
    BpmnInstanceSerializer,
)
import yaml
from api.config import BASE_PATH, BPMN_CHAINCODE_STORE
from api.common import ok, err
from api.models import (
    BPMN,
    BPMNInstance,
    BPMNBindingRecord,
    ChainCode,
    Environment,
    LoleidoOrganization,
    ResourceSet,
    UserProfile,
    Consortium,
    Membership,
)
from zipfile import ZipFile
import json


# from api.routes.bpmn  import BpmnCreateBody
from rest_framework import viewsets, status
from requests import get, post


class BPMNViewsSet(viewsets.ModelViewSet):
    # 应该要新增这一个接口
    # TODO: 不是很理解多实例如何存储，所以逻辑应该不对..
    @action(methods=["post"], detail=True, url_path="createMuti")
    def createMulti(self, request, *args, **kwargs):
        """
        创建多实例Bpmn绑定实例
        """
        bpmn_instance_id = request.parser_context["kwargs"].get(
            "bpmn_instance_id", None
        )
        try:
            bpmn_instance = BPMNInstance.objects.get(pk=bpmn_instance_id)
        except BPMNInstance.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        membership_ids = request.data.get("membership_ids", None)
        memberships = []
        try:
            for membership_id in membership_ids:
                memberships.append(Membership.objects.get(pk=membership_id))
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        participant_id = request.data.get("participant_id", None)
        serializer = []
        for membership in memberships:
            bpmn_binding_record = BPMNBindingRecord.objects.create(
                bpmn_instance=bpmn_instance,
                membership=membership,
                participant_id=participant_id,
            )
            serializer.append(BpmnBindingRecordSerializer(bpmn_binding_record))
        self._check(bpmn_instance_id)
        return Response(data=ok(serializer), status=status.HTTP_201_CREATED)

  