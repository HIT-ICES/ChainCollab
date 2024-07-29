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
    BpmnListSerializer,
    BpmnSerializer,
    BpmnInstanceSerializer,
    DmnSerializer,
)
import yaml
from api.config import BASE_PATH, BPMN_CHAINCODE_STORE, CURRENT_IP
from api.common import ok, err
from api.models import (
    BPMN,
    DMN,
    BPMNInstance,
    ChainCode,
    Environment,
    LoleidoOrganization,
    Consortium,
)
from zipfile import ZipFile
import json

# from api.routes.bpmn  import BpmnCreateBody
from rest_framework import viewsets, status
from requests import get, post


class BPMNViewsSet(viewsets.ModelViewSet):

    @action(methods=["post"], detail=False, url_path="_upload")
    def upload(self, request, pk=None, *args, **kwargs):
        try:
            consortiumid = request.data.get("consortiumid")
            orgid = request.data.get("orgid")
            name = request.data.get("name")
            bpmnContent = request.data.get("bpmnContent")
            svgContent = request.data.get("svgContent")
            raw_participants = request.data.get("participants")  # [P1,P2]
            participants = [
                {"id": recordkey, "name": raw_participants[recordkey]}
                for recordkey in raw_participants.keys()
            ]
            consortium = Consortium.objects.get(id=consortiumid)
            organization = LoleidoOrganization.objects.get(id=orgid)

            bpmn = BPMN(
                # consortium = consortium,
                organization=organization,
                consortium=consortium,
                name=name,
                svgContent=svgContent,
                bpmnContent=bpmnContent,
                participants=json.dumps(participants),
                status="Initiated",
            )

            bpmn.save()

            return Response(
                data=ok("bpmn file storaged success"), status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["get"], detail=False, url_path="_list")
    def list_all(self, request, pk=None, *args, **kwargs):
        try:
            bpmns = BPMN.objects.all()
            serializer = BpmnListSerializer(bpmns, many=True)
            return Response(data=ok(serializer.data), status=status.HTTP_200_OK)

        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        """
        更新Bpmn实例
        """
        try:
            bpmn = BPMN.objects.get(pk=pk)
            if "bpmn_id" in request.data:
                bpmn.bpmn_id = request.data.get("bpmn_id")
            if "name" in request.data:
                bpmn.name = request.data.get("name")
            if "status" in request.data:
                bpmn.status = request.data.get("status")
            if "user_id" in request.data:
                bpmn.user_id = request.data.get("user_id")
            if "firefly_url" in request.data:
                bpmn.firefly_url = request.data.get("firefly_url")
            if "envId" in request.data:
                envId = request.data.get("envId")
                bpmn.environment = Environment.objects.get(pk=envId)
            if "events" in request.data:
                bpmn.events = request.data.get("events")

            bpmn.save()
            serializer = BpmnSerializer(bpmn)
            return Response(data=ok(serializer.data), status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Bpmn详情
        """
        try:
            bpmn = BPMN.objects.get(pk=pk)
        except BPMN.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = BpmnSerializer(bpmn)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        获取Bpmn列表
        """
        try:
            bpmns = BPMN.objects.all()
            serializer = BpmnSerializer(bpmns, many=True)
            return Response(ok(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def _zip_folder(self, folder_path, output_path):
        with ZipFile(output_path, "w") as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, folder_path))

    @action(methods=["post"], detail=True, url_path="package")
    def package(self, request, pk, *args, **kwargs):
        try:
            bpmn_id = pk
            orgid = request.data.get("orgId")
            chaincodeContent = request.data.get("chaincodeContent")
            ffiContent = request.data.get("ffiContent")
            bpmn = BPMN.objects.get(pk=bpmn_id)
            env_id = bpmn.environment.id

            with open(
                BPMN_CHAINCODE_STORE + "/chaincode-go-bpmn/chaincode/smartcontract.go",
                "w",
                encoding="utf-8",
            ) as file:
                file.write(chaincodeContent)

            self._zip_folder(
                BPMN_CHAINCODE_STORE, BASE_PATH + "/opt/bpmn_chaincode.zip"
            )

            headers = request.headers
            files = {
                "file": open(file=BASE_PATH + "/opt//bpmn_chaincode.zip", mode="rb")
            }
            response = post(
                f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/package",
                data={
                    "name": bpmn.name.replace(".bpmn", ""),
                    "version": 1,
                    "language": "golang",
                    "org_id": orgid,
                },
                files=files,
                headers={"Authorization": headers["Authorization"]},
            )
            chaincode_id = response.json()["data"]["id"]
            chaincode = ChainCode.objects.get(id=chaincode_id)

            bpmn.ffiContent = ffiContent
            bpmn.chaincode_content = chaincodeContent
            bpmn.chaincode = chaincode
            bpmn.status = "Generated"
            # consortium = consortium,
            bpmn.save()

            return Response(
                data=ok("bpmn file storaged success"), status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)


class BPMNInstanceViewSet(viewsets.ModelViewSet):

    def create(self, request, *args, **kwargs):
        """
        创建Bpmn实例
        """
        try:
            bpmn_id = request.parser_context["kwargs"].get("bpmn_id")
            bpmn = BPMN.objects.get(pk=bpmn_id)
            instance_chaincode_id = request.data.get("instance_chaincode_id")
            name = request.data.get("name")
            bpmn_instance = BPMNInstance.objects.create(
                bpmn=bpmn, instance_chaincode_id=instance_chaincode_id, name=name
            )
            bpmn_instance.save()
            serializer = BpmnInstanceSerializer(bpmn_instance)
            return Response(data=ok(serializer.data), status=status.HTTP_201_CREATED)
        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Bpmn实例详情
        """
        try:
            bpmn_instance = BPMNInstance.objects.get(pk=pk)
            serializer = BpmnInstanceSerializer(bpmn_instance)
            return Response(serializer.data)
        except BPMNInstance.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def list(self, request, *args, **kwargs):
        """
        获取Bpmn实例列表
        """
        try:
            bpmn_id = request.parser_context["kwargs"].get("bpmn_id")
            try:
                bpmn = BPMN.objects.get(pk=bpmn_id)
            except BPMN.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            bpmn_instances = BPMNInstance.objects.filter(bpmn=bpmn)
            serializer = BpmnInstanceSerializer(bpmn_instances, many=True)
            return Response(ok(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def _ends_with_time_format(self, input_string):
        pattern = r"^test-\d{4}-\d{2}-\d{2}-\d{2}\.\d{2}\.\d{2}\.bpmn$"
        if re.match(pattern, input_string):
            return True
        else:
            return False

    def _ends_with_Test(self, input_string):
        pattern = r".*Test.bpmn$"
        if re.match(pattern, input_string):
            return True
        return False


class DmnViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        """
        创建Dmn实例
        """
        try:
            consortiumid = request.data.get("consortiumid")
            orgid = request.data.get("orgid")
            consortium = Consortium.objects.get(id=consortiumid)
            organization = LoleidoOrganization.objects.get(id=orgid)
            dmn = DMN.objects.create(
                consortium=consortium,
                organization=organization,
                name=request.data.get("name"),
                dmnContent=request.data.get("dmnContent"),
                svgContent=request.data.get("svgContent"),
            )
            dmn.save()
            serializer = DmnSerializer(dmn)
            return Response(data=ok(serializer.data), status=status.HTTP_201_CREATED)
        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Dmn详情
        """
        try:
            dmn = DMN.objects.get(pk=pk)
        except DMN.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = DmnSerializer(dmn)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        获取Dmn列表
        """
        try:
            dmns = DMN.objects.all()
            serializer = DmnSerializer(dmns, many=True)
            return Response(ok(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        """
        更新Dmn实例
        """
        try:
            dmn = DMN.objects.get(pk=pk)
            if "dmn_id" in request.data:
                dmn.dmn_id = request.data.get("dmn_id")
            if "name" in request.data:
                dmn.name = request.data.get("name")
            if "dmnContent" in request.data:
                dmn.dmnContent = request.data.get("dmnContent")
            if "dmnSvgContent" in request.data:
                dmn.dmnSvgContent = request.data.get("dmnSvgContent")
            if "consortiumid" in request.data:
                dmn.consortiumid = request.data.get("consortiumid")
            if "orgid" in request.data:
                dmn.orgid = request.data.get("orgid")

            dmn.save()
            serializer = DmnSerializer(dmn)
            return Response(data=ok(serializer.data), status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            raise Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
