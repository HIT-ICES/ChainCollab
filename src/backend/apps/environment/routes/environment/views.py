import json
import logging
import os
import re
import shutil
from pathlib import Path
from uuid import uuid4
from requests import post
from rest_framework import viewsets, status
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from common.enums import EthNodeType, FabricNodeType

from .serializers import EnvironmentSerializer, EthEnvironmentSerializer
from rest_framework.decorators import action, parser_classes

from apps.infra.models import Agent
from apps.ethereum.models import (
    EthereumResourceSet,
    EthNode,
    IdentityDeployment,
    EthereumIdentity,
)
from apps.fabric.models import ResourceSet, FabricResourceSet, Port
from apps.environment.models import Environment, EthEnvironment, Task
from apps.core.models import Consortium, Membership, LoleidoOrganization
from apps.api.config import (
    DEFAULT_AGENT,
    DEFAULT_CHANNEL_NAME,
    FABRIC_CONFIG,
    CURRENT_IP,
    ORACLE_CONTRACT_PATH,
    DMN_CONTRACT_PATH,
    ETHEREUM_CONTRACT_STORE,
)
from common.lib.fabric.chaincode_flow import install_fabric_chaincode_flow
from common.utils.test_time import timeitwithname
from apps.environment.services.chainlink_orchestrator import ChainlinkOrchestrator
from apps.environment.services.dmn_firefly import (
    dmn_abi_fingerprint,
    contract_event_names,
    build_listener_payload,
    register_dmn_contract_to_firefly,
    register_related_chainlink_contracts_to_firefly,
)
from apps.environment.services.firefly_orchestrator import FireflyOrchestrator
from apps.environment.services.identity_orchestrator import IdentityOrchestrator
from apps.environment.services.task_runtime import (
    create_task,
    create_task_with_status_transition,
    _ensure_idempotent_task_request,
    _start_task_async,
)

LOG = logging.getLogger("api")


class EnvironmentViewSet(viewsets.ViewSet):
    """
    Environment管理
    """
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """
        获取Environment列表
        """
        consortium_id = request.parser_context["kwargs"].get("consortium_id")
        queryset = Environment.objects.filter(consortium_id=consortium_id)
        serializer = EnvironmentSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        创建Environment
        """
        consortium_id = request.parser_context["kwargs"].get("consortium_id")
        name = request.data.get("name")
        try:
            consortium = Consortium.objects.get(pk=consortium_id)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        environment = Environment.objects.create(consortium=consortium, name=name)
        environment.save()
        serializer = EnvironmentSerializer(environment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Environment详情
        """
        try:
            environment = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = EnvironmentSerializer(environment)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """
        更新Environment
        """
        try:
            environment = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        environment.name = request.data.get("name")
        environment.save()
        serializer = EnvironmentSerializer(environment)
        return Response(serializer.data)

    def destroy(self, request, pk=None, *args, **kwargs):
        """
        删除Environment
        """
        try:
            environment = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        environment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnvironmentOperateViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _start_task(self, task, handler, *args, **kwargs):
        _start_task_async(
            task,
            handler,
            *args,
            rollback_model=Environment,
            rollback_target_type="Environment",
            **kwargs,
        )

    def _ensure_idempotent_task(self, request, env_id: str, task_type: str, mode: str | None = None):
        return _ensure_idempotent_task_request(request, env_id, task_type, mode)

    def _run_chaincode_install(
        self,
        env_id: str,
        *,
        file_path: str,
        chaincode_name: str,
        auth: str,
        org_id: str | None,
        status_field: str,
        language: str | None = None,
    ):
        env = Environment.objects.get(pk=env_id)
        kwargs = {
            "env": env,
            "file_path": file_path,
            "chaincode_name": chaincode_name,
            "auth": auth,
            "org_id": org_id,
            "status_field": status_field,
        }
        if language:
            kwargs["language"] = language
        return install_fabric_chaincode_flow(**kwargs)

    @action(methods=["post"], detail=True, url_path="init")
    @timeitwithname("Init")
    def init(self, request, pk=None, *args, **kwargs):
        """
        初始化Environment,
        生成一个系统资源组，创建CA，生成MSP，提供一个Orderer节点
        """
        env = Environment.objects.get(pk=pk)

        if env.status != "CREATED":
            return Response(
                {"message": "Environment has been initialized"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consortium = env.consortium

        system_org = LoleidoOrganization.objects.create(
            name=consortium.name + env.name + "-system",
        )

        membership = Membership.objects.create(
            name=env.name + "-system",
            loleido_organization=system_org,
            consortium=consortium,
        )

        agent = Agent.objects.create(
            name="system-agent",
            type=DEFAULT_AGENT["type"],
            urls=DEFAULT_AGENT["urls"],
            status="active",
        )

        resource_set = ResourceSet.objects.create(
            name=membership.name, environment=env, membership=membership, agent=agent
        )
        fabric_resource_set = FabricResourceSet.objects.create(
            resource_set=resource_set,
            org_type=1,
            name=membership.name + ".org" + ".com",
            msp=membership.name + ".org" + ".com" + "OrdererMSP",
        )
        # #  ALL CERATED

        # # CA
        # # HOW TO CREATE A CA?
        # # TODO access api from backend for CA
        headers = request.headers
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/ca_create",
            data={},
            headers={"Authorization": headers["Authorization"]},
        )
        LOG.info(
            "Init env %s -> ca_create resource_set %s",
            env.id,
            resource_set.id,
        )

        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/enroll_org_ca_admin",
            data={},
            headers={"Authorization": headers["Authorization"]},
        )
        LOG.info(
            "Init env %s -> enroll_org_ca_admin resource_set %s",
            env.id,
            resource_set.id,
        )

        # Register Org Admin
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/org_user_admin/register_enroll",
            data={},
            headers={"Authorization": headers["Authorization"]},
        )
        LOG.info(
            "Init env %s -> org_user_admin/register_enroll resource_set %s",
            env.id,
            resource_set.id,
        )

        node_name = "orderer0"
        orderer_domain_name = f"{node_name}.{fabric_resource_set.name.split('.', 1)[1]}"

        # # Register Orderer Node
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/register_enroll",
            data={
                "node_url": orderer_domain_name,
                "node_type": FabricNodeType.Orderer.value,
            },
            headers={"Authorization": headers["Authorization"]},
        )
        LOG.info(
            "Init env %s -> register_enroll orderer %s (resource_set %s)",
            env.id,
            orderer_domain_name,
            resource_set.id,
        )

        # 创建节点
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/nodes",
            data={
                "num": 1,
                "type": "orderer",
                "name": node_name,
            },
            headers={"Authorization": headers["Authorization"]},
        )
        LOG.info(
            "Init env %s -> create orderer node %s (resource_set %s)",
            env.id,
            node_name,
            resource_set.id,
        )

        # Register System peer node
        node_name = "peer0"
        peer_domain_name = f"{node_name}.{fabric_resource_set.name}"
        LOG.info(
            "Init env %s -> prepare peer node name=%s domain=%s (resource_set %s)",
            env.id,
            node_name,
            peer_domain_name,
            resource_set.id,
        )
        # # Register Peer Node
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/register_enroll",
            data={
                "node_url": peer_domain_name,
                "node_type": FabricNodeType.Peer.value,
            },
            headers={"Authorization": headers["Authorization"]},
        )
        LOG.info(
            "Init env %s -> register_enroll peer %s (resource_set %s)",
            env.id,
            peer_domain_name,
            resource_set.id,
        )

        # 创建节点
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/nodes",
            data={"num": 1, "type": "peer", "name": node_name},
            headers={"Authorization": headers["Authorization"]},
        )
        LOG.info(
            "Init env %s -> create peer node %s (resource_set %s)",
            env.id,
            node_name,
            resource_set.id,
        )

        env.status = "INITIALIZED"
        env.save()
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="join")
    @timeitwithname("Join")
    def join(self, request, pk=None, *args, **kwargs):
        """
        参与Environment
        为参与Environment的Membership创建资源组，创建CA，生成MSP，同时创建默认的peer节点
        """
        membership_id = request.data.get("membership_id", None)
        try:
            membership = Membership.objects.get(pk=membership_id)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            environment = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if environment.status != "INITIALIZED":
            return Response(
                {"message": "Environment has not been initialized or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = membership.loleido_organization
        agent = Agent.objects.create(
            name="system-agent",
            type=DEFAULT_AGENT["type"],
            urls=DEFAULT_AGENT["urls"],
            status="active",
            organization=org,
        )
        resource_set = ResourceSet.objects.create(
            name=membership.name,
            environment=environment,
            membership=membership,
            agent=agent,
        )

        fabric_resource_set = FabricResourceSet.objects.create(
            resource_set=resource_set,
            org_type=0,
            name=membership.name + ".org" + ".com",
            msp=membership.name.capitalize() + ".org" + ".com" + "MSP",
        )

        # Create CA for it
        headers = request.headers
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/ca_create",
            data={},
            headers={"Authorization": headers["Authorization"]},
        )
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/enroll_org_ca_admin",
            data={},
            headers={"Authorization": headers["Authorization"]},
        )

        # Register Org Admin
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/org_user_admin/register_enroll",
            data={},
            headers={"Authorization": headers["Authorization"]},
        )

        node_name = "peer0"
        peer_domain_name = f"{node_name}.{fabric_resource_set.name}"
        LOG.info(
            "Join env %s -> prepare peer node name=%s domain=%s (resource_set %s)",
            environment.id,
            node_name,
            peer_domain_name,
            resource_set.id,
        )
        # # Register Peer Node
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/cas/register_enroll",
            data={
                "node_url": peer_domain_name,
                "node_type": FabricNodeType.Peer.value,
            },
            headers={"Authorization": headers["Authorization"]},
        )

        # 创建节点
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/nodes",
            data={"num": 1, "type": "peer", "name": node_name},
            headers={"Authorization": headers["Authorization"]},
        )

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="start")
    @timeitwithname("Start")
    def start(self, request, pk=None, *args, **kwargs):
        """
        启动network——系统通道
        """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "INITIALIZED":
            return Response(
                {"message": "Environment has not been initialized or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers
        post(
            f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/networks",
            data={
                "consensus": "raft",
                "database": "leveldb",
                "name": "system-network",
            },
            headers={"Authorization": headers["Authorization"]},
        )
        env = Environment.objects.get(pk=pk)
        env.status = "STARTED"
        env.save()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="activate")
    @timeitwithname("Activate")
    def activate(self, request, pk=None, *args, **kwargs):
        """
        激活环境，创建一个默认channel，并使得所有的peer加入到channel中
        """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "STARTED":
            return Response(
                {"message": "Environment has not been started or has activated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers

        orderer_resource_sets = env.resource_sets.all().filter(
            sub_resource_set__org_type=1
        )  # 0: UserOrg 1: SystemOrg

        def flatten(xss):
            return [x for xs in xss for x in xs]

        orderer_ids = flatten(
            [
                [
                    str(node.id)
                    for node in orderer_resource_set.sub_resource_set.node.all()
                    if node.type != "ca" and node.type != "peer"
                ]
                for orderer_resource_set in orderer_resource_sets
            ]
        )
        peer_resource_sets = env.resource_sets.all().filter(
            sub_resource_set__org_type=0
        )  # 0: UserOrg 1: SystemOrg
        peer_ids = flatten(
            [
                [
                    str(node.id)
                    for node in peer_resource_set.sub_resource_set.node.all()
                    if node.type != "ca"
                ]
                for peer_resource_set in peer_resource_sets
            ]
        )

        # append orderer resource peers
        peer_ids.extend(
            flatten(
                [
                    [
                        str(node.id)
                        for node in orderer_resource_set.sub_resource_set.node.all()
                        if node.type != "ca" and node.type != "orderer"
                    ]
                    for orderer_resource_set in orderer_resource_sets
                ]
            )
        )

        if not orderer_ids or not peer_ids:
            return Response(
                {
                    "message": "No orderers or peers found to create channel",
                    "orderers": orderer_ids,
                    "peers": peer_ids,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        channel_name = DEFAULT_CHANNEL_NAME
        response = post(
            f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/channels",
            json={
                "orderers": orderer_ids,
                "peers": peer_ids,
                "name": channel_name,
                "environment_id": str(env.id),
            },
            headers={"Authorization": headers["Authorization"]},
        )

        if not str(response.status_code).startswith("2"):
            raise Exception(
                f"Create channel failed: {response.status_code} {response.text}"
            )
        try:
            payload = response.json()
        except Exception:
            raise Exception(f"Create channel failed: invalid JSON {response.text}")

        channel_id = (
            payload.get("data", {}).get("id") if isinstance(payload, dict) else None
        ) or (payload.get("id") if isinstance(payload, dict) else None)
        if not channel_id:
            raise Exception(f"Channel ID missing in response: {payload}")

        def _generateAnchorPeers(peer_resource_set):
            peer_nodes = [
                str(node.id)
                for node in peer_resource_set.sub_resource_set.node.all()
                if node.type != "ca" and node.type != "orderer"
            ]
            if not peer_nodes:
                LOG.warning(
                    "Skip anchor peer generation: no peer nodes found for resource_set=%s",
                    peer_resource_set.id,
                )
                return
            post(
                f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/channels/{channel_id}/anchors",
                data={
                    "anchor_peers": [peer_nodes[0]],
                    "orderers": orderer_ids,
                    "resource_set_id": peer_resource_set.id,
                },
                headers={"Authorization": headers["Authorization"]},
            )
            post(
                f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{peer_resource_set.id}/cas/ccp/generate",
                data={
                    "channel_name": channel_name,
                    "peer_id": peer_nodes[0],
                },
                headers={"Authorization": headers["Authorization"]},
            )

        for peer_resource_set in peer_resource_sets:
            _generateAnchorPeers(peer_resource_set)

        for orderer_resource_set in orderer_resource_sets:
            _generateAnchorPeers(orderer_resource_set)

        env.status = "ACTIVATED"
        env.save()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="start_firefly")
    def start_firefly(self, request, pk=None, *args, **kwargs):
        """
        启动Firefly 以及 其他组件
        """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status not in ["ACTIVATED", "STARTED"]:
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "FABRIC_FIREFLY_START"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        headers = request.headers
        task, _ = create_task_with_status_transition(
            task_type="FABRIC_FIREFLY_START",
            target_type="Environment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            target_obj=env,
            status_field="firefly_status",
            pending_value="PENDING",
        )

        def _start_firefly_flow(env_id: str, auth: str):
            post(
                f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/fireflys/init",
                headers={"Authorization": auth},
            )
            post(
                f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/fireflys/start",
                headers={"Authorization": auth},
            )
            Environment.objects.filter(pk=env_id).update(firefly_status="STARTED")
            return {"status": "STARTED"}

        self._start_task(task, _start_firefly_flow, str(env.id), headers["Authorization"])

        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="install_firefly")
    def install_firefly(self, request, pk=None, *args, **kwargs):
        """
        安装Firefly
        """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status not in ["ACTIVATED", "STARTED"]:
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "FABRIC_FIREFLY_INSTALL"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        headers = request.headers
        org_id = request.data.get("org_id")
        task, _ = create_task_with_status_transition(
            task_type="FABRIC_FIREFLY_INSTALL",
            target_type="Environment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            target_obj=env,
            status_field="firefly_status",
            pending_value="PENDING",
        )
        self._start_task(
            task,
            self._run_chaincode_install,
            env.id,
            file_path=FABRIC_CONFIG + "/firefly-go.zip",
            chaincode_name="Firefly",
            auth=headers["Authorization"],
            org_id=org_id,
            status_field="firefly_status",
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="install_oracle")
    def install_oracle(self, request, pk=None, *args, **kwargs):
        """ """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status not in ["ACTIVATED", "STARTED"]:
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "FABRIC_ORACLE_INSTALL"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        headers = request.headers
        org_id = request.data.get("org_id")
        task, _ = create_task_with_status_transition(
            task_type="FABRIC_ORACLE_INSTALL",
            target_type="Environment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            target_obj=env,
            status_field="Oracle_status",
            pending_value="PENDING",
        )
        self._start_task(
            task,
            self._run_chaincode_install,
            env.id,
            file_path=ORACLE_CONTRACT_PATH + "/oracle-go.zip",
            chaincode_name="Oracle",
            auth=headers["Authorization"],
            org_id=org_id,
            status_field="Oracle_status",
        )

        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="install_dmn_engine")
    def install_dmn_engine(self, request, pk=None, *args, **kwargs):
        """
        启动DMN Engine: 部署合约
        """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status not in ["ACTIVATED", "STARTED"]:
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "FABRIC_DMN_INSTALL"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        headers = request.headers
        org_id = request.data.get("org_id")
        task, _ = create_task_with_status_transition(
            task_type="FABRIC_DMN_INSTALL",
            target_type="Environment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            target_obj=env,
            status_field="DMN_status",
            pending_value="PENDING",
        )
        self._start_task(
            task,
            self._run_chaincode_install,
            env.id,
            file_path=DMN_CONTRACT_PATH + "/dmn-engine.zip",
            chaincode_name="DMNEngine",
            auth=headers["Authorization"],
            org_id=org_id,
            language="java",
            status_field="DMN_status",
        )

        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["get"], detail=False, url_path="requestOracleFFI")
    def requestOracleFFI(self, request, pk=None, *args, **kwargs):
        """
        请求Oracle FFI
        """
        with open(ORACLE_CONTRACT_PATH + "/oracleFFI.json", "r") as f:
            ffiContent = f.read()

        response = {"ffiContent": ffiContent}

        return Response(response, status=status.HTTP_200_OK)

class EthEnvironmentViewSet(viewsets.ModelViewSet):
    serializer_class = EthEnvironmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        consortium_id = self.kwargs.get("consortium_id")
        if consortium_id:
            return EthEnvironment.objects.filter(consortium_id=consortium_id)
        return EthEnvironment.objects.all()

    def create(self, request, *args, **kwargs):
        """
        创建EthEnvironment
        """
        consortium_id = request.parser_context["kwargs"].get("consortium_id")
        name = request.data.get("name")
        try:
            consortium = Consortium.objects.get(pk=consortium_id)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        environment = EthEnvironment.objects.create(consortium=consortium, name=name)
        environment.save()
        serializer = EthEnvironmentSerializer(environment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """
        获取EthEnvironment列表
        """
        consortium_id = request.parser_context["kwargs"].get("consortium_id")
        queryset = EthEnvironment.objects.filter(consortium_id=consortium_id)
        serializer = EthEnvironmentSerializer(queryset, many=True)
        return Response(serializer.data)

class EthEnvironmentOperateViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    ETH_SYSTEM_ACCOUNT = "0x365Acf78C44060CAF3A4789D804Df11E3B4AA17d"

    def _ensure_idempotent_task(self, request, env_id: str, task_type: str, mode: str | None = None):
        return _ensure_idempotent_task_request(request, env_id, task_type, mode)

    def _start_task(self, task, handler, *args, **kwargs):
        _start_task_async(
            task,
            handler,
            *args,
            rollback_model=EthEnvironment,
            rollback_target_type="EthEnvironment",
            **kwargs,
        )

    def _identity_orchestrator(self) -> IdentityOrchestrator:
        return IdentityOrchestrator(logger=LOG)

    def _firefly_orchestrator(self) -> FireflyOrchestrator:
        return FireflyOrchestrator(logger=LOG)

    def _chainlink_orchestrator(self) -> ChainlinkOrchestrator:
        return ChainlinkOrchestrator(
            logger=LOG,
            eth_system_account=self.ETH_SYSTEM_ACCOUNT,
            set_task_step=self._set_task_step,
            resolve_system_rpc_url=self._resolve_system_rpc_url,
        )

    def _set_task_step(self, task_id: str | None, step: str):
        if not task_id:
            return
        try:
            Task.objects.filter(pk=task_id).update(step=step, updated_at=timezone.now())
        except Exception:
            LOG.exception("Task %s step update failed", task_id)

    def _require_started_or_activated(
        self,
        env: EthEnvironment,
        *,
        message: str = "Environment has not been activated or has started",
    ):
        if env.status not in ["ACTIVATED", "STARTED"]:
            return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)
        return None

    def _get_eth_env_or_404(self, pk):
        try:
            return EthEnvironment.objects.get(pk=pk), None
        except EthEnvironment.DoesNotExist:
            return None, Response(status=status.HTTP_404_NOT_FOUND)

    def _sanitize_upload_name(self, filename: str) -> str:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or "identity-contract.zip")
        return safe_name[:200] or "identity-contract.zip"

    def _store_identity_archive_upload(self, uploaded_file) -> str:
        upload_root = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract", "uploads")
        os.makedirs(upload_root, exist_ok=True)
        safe_name = self._sanitize_upload_name(getattr(uploaded_file, "name", "identity-contract.zip"))
        archive_path = os.path.join(upload_root, f"{uuid4()}-{safe_name}")
        with open(archive_path, "wb") as handle:
            for chunk in uploaded_file.chunks():
                handle.write(chunk)
        return archive_path

    def _enqueue_eth_chaincode_install(
        self,
        request,
        env: EthEnvironment,
        *,
        task_type: str,
        status_field: str,
        file_path: str,
        chaincode_name: str,
        org_id: str | None,
        language: str | None = None,
    ) -> Response:
        idempotent = self._ensure_idempotent_task(request, str(env.id), task_type)
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        headers = request.headers
        task, _ = create_task_with_status_transition(
            task_type=task_type,
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            target_obj=env,
            status_field=status_field,
            pending_value="PENDING",
        )
        self._start_task(
            task,
            self._run_chaincode_install,
            env.id,
            file_path=file_path,
            chaincode_name=chaincode_name,
            auth=headers["Authorization"],
            org_id=org_id,
            language=language,
            status_field=status_field,
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    def _rpc_call(self, rpc_url: str, method: str, params=None):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
        response = post(rpc_url, json=payload, timeout=8)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data.get("result")

    def _resolve_system_rpc_url(self, env: EthEnvironment) -> str:
        system_resource_set = env.resource_sets.filter(
            ethereum_sub_resource_set__org_type=1
        ).first()
        if not system_resource_set:
            raise ValueError("system resource set not found")

        system_node = EthNode.objects.filter(
            fabric_resource_set__resource_set=system_resource_set
        ).first()
        if not system_node:
            raise ValueError("system node not found")

        rpc_port = Port.objects.filter(eth_node=system_node, internal=8545).first()
        if not rpc_port:
            raise ValueError("system node RPC port (8545) not found")

        return f"http://{CURRENT_IP}:{rpc_port.external}"

    def _check_system_account_available(self, env: EthEnvironment, expected_account: str | None = None) -> dict:
        account = (expected_account or self.ETH_SYSTEM_ACCOUNT).lower()
        rpc_url = self._resolve_system_rpc_url(env)
        accounts = self._rpc_call(rpc_url, "eth_accounts", []) or []
        normalized_accounts = [a.lower() for a in accounts if isinstance(a, str)]
        has_expected = account in normalized_accounts

        result = {
            "rpc_url": rpc_url,
            "expected_account": account,
            "accounts": accounts,
            "has_expected_account": has_expected,
            "unlock_ok": False,
            "balance_wei": None,
            "unlock_error": None,
        }

        if has_expected:
            try:
                unlocked = self._rpc_call(
                    rpc_url,
                    "personal_unlockAccount",
                    [account, "", 5],
                )
                result["unlock_ok"] = bool(unlocked)
            except Exception as exc:
                result["unlock_error"] = str(exc)

            try:
                result["balance_wei"] = self._rpc_call(
                    rpc_url,
                    "eth_getBalance",
                    [account, "latest"],
                )
            except Exception as exc:
                result["balance_wei"] = None
                result["balance_error"] = str(exc)

        return result

    def _resolve_chainlink_scripts(self) -> dict:
        return self._chainlink_orchestrator().resolve_chainlink_scripts()

    def _sync_chainlink_cluster(
        self,
        env: EthEnvironment,
        persist: bool = True,
        include_jobs: bool = True,
    ) -> dict:
        return self._chainlink_orchestrator().sync_chainlink_cluster(
            env,
            persist=persist,
            include_jobs=include_jobs,
        )

    def _run_chainlink_setup(
        self,
        env_id: str,
        mode: str = "lite",
        task_id: str | None = None,
    ) -> dict:
        result = self._chainlink_orchestrator().run_chainlink_setup(
            env_id,
            mode=mode,
            task_id=task_id,
        )
        try:
            result["firefly_registration"] = self._auto_register_dmn_firefly_after_deploy(
                env_id,
                task_id=task_id,
            )
        except Exception as exc:
            LOG.warning(
                "DMNContract action=auto_register_after_chainlink_setup_failed env=%s error=%s",
                env_id,
                exc,
            )
            result["firefly_registration_error"] = str(exc)
        return result

    def _run_chainlink_create_job(
        self,
        env_id: str,
        recreate: bool = False,
        external_job_id: str | None = None,
        sync_onchain: bool = True,
        job_kind: str = "dmn",
        data_source_url: str | None = None,
        data_source_method: str = "GET",
        task_id: str | None = None,
    ) -> dict:
        return self._chainlink_orchestrator().run_chainlink_create_job(
            env_id,
            recreate=recreate,
            external_job_id=external_job_id,
            sync_onchain=sync_onchain,
            job_kind=job_kind,
            data_source_url=data_source_url,
            data_source_method=data_source_method,
            task_id=task_id,
        )

    def _redeploy_dmn_contract(
        self,
        env_id: str,
        contract_name: str,
        task_id: str | None = None,
    ) -> dict:
        return self._chainlink_orchestrator().redeploy_dmn_contract(
            env_id,
            contract_name=contract_name,
            task_id=task_id,
        )

    def _load_chainlink_deployments(self) -> dict:
        return self._chainlink_orchestrator().load_chainlink_deployments()

    def _get_dmn_contract_name(self) -> str:
        return os.environ.get("DMN_CONTRACT_NAME") or (
            "MyChainlinkRequesterDMN_Lite"
            if os.environ.get("DMN_MODE") == "lite"
            else "MyChainlinkRequesterDMN"
        )

    def _resolve_dmn_contract_name(self, dmn_deployment: dict | None = None) -> str:
        dmn_deployment = dmn_deployment or {}
        contract_name = (
            dmn_deployment.get("contractName")
            or dmn_deployment.get("contract_name")
            or dmn_deployment.get("name")
        )
        if contract_name:
            return str(contract_name)
        return self._get_dmn_contract_name()

    def _resolve_dmn_contract_abi_hash(
        self,
        compiled: dict,
        contract_name: str,
    ) -> str | None:
        _, abi_hash = dmn_abi_fingerprint(compiled, contract_name)
        return abi_hash

    def _extract_request_id(self, payload: dict | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        def normalize(candidate: object) -> str | None:
            if not isinstance(candidate, str):
                return None
            raw = candidate.strip()
            if not raw:
                return None
            if raw.startswith("0x") and len(raw) == 66:
                return raw.lower()
            if len(raw) == 64:
                try:
                    int(raw, 16)
                    return f"0x{raw.lower()}"
                except Exception:
                    return None
            return None

        direct = normalize(payload.get("requestId") or payload.get("request_id"))
        if direct:
            return direct
        output = payload.get("output")
        if isinstance(output, dict):
            for key in ("result", "body", "data", "response", "value"):
                nested = self._extract_request_id(output.get(key))
                if nested:
                    return nested
            headers = output.get("headers")
            if isinstance(headers, dict):
                request_id = normalize(headers.get("requestId") or headers.get("request_id"))
                if request_id:
                    return request_id
        for key in ("headers", "result", "data", "response", "body", "value"):
            value = payload.get(key)
            if isinstance(value, dict):
                nested = self._extract_request_id(value)
                if nested:
                    return nested
            elif isinstance(value, str):
                normalized = normalize(value)
                if normalized:
                    return normalized
        return None

    def _extract_transaction_hash(self, payload: dict | None) -> str | None:
        if not isinstance(payload, dict):
            return None

        def normalize(candidate: object) -> str | None:
            if not isinstance(candidate, str):
                return None
            raw = candidate.strip()
            if not raw:
                return None
            if raw.startswith("0x") and len(raw) == 66:
                return raw.lower()
            if len(raw) == 64:
                try:
                    int(raw, 16)
                    return f"0x{raw.lower()}"
                except Exception:
                    return None
            return None

        direct = normalize(
            payload.get("transactionHash")
            or payload.get("transaction_hash")
            or payload.get("tx")
        )
        if direct:
            return direct

        output = payload.get("output")
        if isinstance(output, dict):
            for key in ("result", "body", "data", "response", "value", "headers"):
                nested = self._extract_transaction_hash(output.get(key))
                if nested:
                    return nested
            nested = normalize(output.get("transactionHash") or output.get("transaction_hash"))
            if nested:
                return nested

        for key in ("headers", "result", "data", "response", "body", "value"):
            value = payload.get(key)
            if isinstance(value, dict):
                nested = self._extract_transaction_hash(value)
                if nested:
                    return nested
            elif isinstance(value, str):
                normalized = normalize(value)
                if normalized:
                    return normalized
        return None

    def _extract_request_id_from_receipt(
        self,
        receipt: dict | None,
        contract_address: str,
    ) -> str | None:
        if not isinstance(receipt, dict):
            return None
        target_address = str(contract_address or "").strip().lower()
        logs = receipt.get("logs") or []
        if not isinstance(logs, list):
            return None

        def normalize_topic(candidate: object) -> str | None:
            if not isinstance(candidate, str):
                return None
            raw = candidate.strip()
            if not raw:
                return None
            if raw.startswith("0x") and len(raw) == 66:
                return raw.lower()
            if len(raw) == 64:
                try:
                    int(raw, 16)
                    return f"0x{raw.lower()}"
                except Exception:
                    return None
            return None

        for log in logs:
            if not isinstance(log, dict):
                continue
            log_address = str(log.get("address") or "").strip().lower()
            if target_address and log_address != target_address:
                continue
            topics = log.get("topics") or []
            if not isinstance(topics, list) or len(topics) < 2:
                continue
            request_id = normalize_topic(topics[1])
            if request_id:
                return request_id
        return None

    def _get_dmn_api_name(
        self,
        env: EthEnvironment,
        compiled: dict | None = None,
        dmn_deployment: dict | None = None,
    ) -> str:
        dmn_deployment = dmn_deployment or {}
        contract_address = dmn_deployment.get("contractAddress")
        contract_name = self._resolve_dmn_contract_name(dmn_deployment)
        abi_suffix = None
        if compiled:
            abi_suffix = self._resolve_dmn_contract_abi_hash(compiled, contract_name)
        if contract_address:
            base = f"DMNRequest-{str(contract_address)[-6:]}"
            if abi_suffix:
                return f"{base}-{abi_suffix[:6]}"
            return base
        return f"DMNRequest-{str(env.id)[:8]}"

    def _get_data_task_api_name(self, env: EthEnvironment) -> str:
        return f"DataTaskAdapter-{str(env.id)[:8]}"

    def _get_compute_task_api_name(self, env: EthEnvironment) -> str:
        return f"ComputeTaskAdapter-{str(env.id)[:8]}"

    def _get_relayer_api_name(self, env: EthEnvironment) -> str:
        return f"CrossChainAdapter-{str(env.id)[:8]}"

    def _run_oracle_task_suite_setup(
        self,
        env_id: str,
        task_id: str | None = None,
    ) -> dict:
        return self._chainlink_orchestrator().run_oracle_task_suite_setup(
            env_id,
            task_id=task_id,
        )

    def _run_relayer_setup(
        self,
        env_id: str,
        task_id: str | None = None,
    ) -> dict:
        return self._chainlink_orchestrator().run_relayer_adapter_setup(
            env_id,
            task_id=task_id,
        )

    def _resolve_oracle_task_suite(
        self,
        env: EthEnvironment,
        payload_detail: dict | None = None,
    ) -> dict:
        payload_detail = payload_detail or {}
        chainlink_detail = env.chainlink_detail or {}
        suite = {}
        if isinstance(chainlink_detail, dict):
            suite = chainlink_detail.get("oracle_task_suite") or {}
        if not suite:
            suite = payload_detail.get("oracle_task_suite") or {}
        return suite if isinstance(suite, dict) else {}

    def _resolve_relayer_deployment(
        self,
        env: EthEnvironment,
        payload_detail: dict | None = None,
    ) -> dict:
        payload_detail = payload_detail or {}
        chainlink_detail = env.chainlink_detail or {}
        relayer = {}
        if isinstance(chainlink_detail, dict):
            relayer = chainlink_detail.get("relayer") or {}
        if not relayer:
            relayer = payload_detail.get("relayer_deployment") or {}
        return relayer if isinstance(relayer, dict) else {}

    def _register_oracle_task_adapter_firefly(
        self,
        *,
        env: EthEnvironment,
        compiled: dict,
        contract_name: str,
        contract_address: str,
        api_name: str,
    ) -> dict | None:
        if not contract_address:
            return None

        try:
            firefly_core_url = self._identity_orchestrator().get_firefly_core_url(env)
        except Exception as exc:
            LOG.warning(
                "OracleTask action=firefly_core_not_found env=%s contract=%s err=%s",
                env.id,
                contract_name,
                exc,
            )
            return None

        contract_key = f"contracts/{contract_name}.sol:{contract_name}"
        abi = (compiled.get("contracts") or {}).get(contract_key, {}).get("abi")
        if not abi:
            LOG.warning(
                "OracleTask action=firefly_missing_abi env=%s contract=%s key=%s",
                env.id,
                contract_name,
                contract_key,
            )
            return None

        ff = self._firefly_orchestrator()
        ffi = ff.generate_ffi(
            firefly_core_url,
            abi,
            name=contract_name,
            namespace="default",
            version="1.0",
            description=f"{contract_name} contract interface",
            version_suffix=str(env.id)[:8],
        )
        interface_payload = ff.register_interface(
            firefly_core_url,
            ffi,
            namespace="default",
            confirm=True,
        )
        interface_id = interface_payload.get("id") or (
            interface_payload.get("interface") or {}
        ).get("id")
        if not interface_id:
            return None

        api_payload = ff.register_api(
            firefly_core_url,
            api_name,
            interface_id,
            contract_address,
            namespace="default",
            confirm=True,
        )
        listeners: list[dict] = []
        for event_name in contract_event_names(abi):
            listener_name = f"{api_name}-{event_name}"
            listener_payload = build_listener_payload(
                listener_name=listener_name,
                interface_id=interface_id,
                contract_address=contract_address,
                event_name=event_name,
                first_event="newest",
            )
            registered_listener = ff.register_listener(
                firefly_core_url,
                listener_payload,
                namespace="default",
                confirm=True,
            )
            listeners.append(
                {
                    "name": listener_name,
                    "event_path": event_name,
                    "payload": registered_listener,
                }
            )
        return {
            "firefly_core_url": firefly_core_url,
            "firefly_interface_id": interface_id,
            "firefly_api_name": api_name,
            "firefly_api_payload": api_payload,
            "firefly_listeners": listeners,
        }

    def _register_dmn_firefly(
        self,
        env: EthEnvironment,
        dmn_deployment: dict,
        compiled: dict,
    ) -> dict | None:
        contract_name = self._resolve_dmn_contract_name(dmn_deployment)
        api_name = self._get_dmn_api_name(env, compiled, dmn_deployment)
        return register_dmn_contract_to_firefly(
            env=env,
            dmn_deployment=dmn_deployment,
            compiled=compiled,
            contract_name=contract_name,
            api_name=api_name,
            identity_flow=self._identity_orchestrator(),
            firefly_manager=self._firefly_orchestrator(),
            logger=LOG,
        )

    def _dmn_firefly_registration_is_current(
        self,
        dmn: dict,
        compiled: dict,
        chainlink_detail: dict | None = None,
    ) -> bool:
        if not dmn.get("firefly_api_name") or not dmn.get("firefly_interface_id"):
            return False
        firefly_core_url = dmn.get("firefly_core_url")
        if not firefly_core_url:
            return False
        contract_name = self._resolve_dmn_contract_name(dmn)
        current_abi_hash = self._resolve_dmn_contract_abi_hash(compiled, contract_name)
        stored_abi_hash = dmn.get("firefly_abi_hash")
        if not current_abi_hash or not stored_abi_hash:
            return False
        listeners = dmn.get("firefly_listeners") or []
        if not isinstance(listeners, list) or not listeners:
            return False
        firefly = self._firefly_orchestrator()
        if not firefly.find_api(firefly_core_url, str(dmn.get("firefly_api_name"))):
            return False
        for listener in listeners:
            if not isinstance(listener, dict):
                return False
            listener_name = listener.get("name")
            if not listener_name or not firefly.find_listener(firefly_core_url, str(listener_name)):
                return False
        chainlink_firefly = {}
        if isinstance(chainlink_detail, dict):
            chainlink_firefly = chainlink_detail.get("firefly") or {}
        related_contracts = chainlink_firefly.get("firefly_related_contracts") or {}
        if not isinstance(related_contracts, dict) or not related_contracts:
            return False
        for contract_payload in related_contracts.values():
            if not isinstance(contract_payload, dict):
                return False
            related_core_url = contract_payload.get("firefly_core_url") or firefly_core_url
            related_api_name = contract_payload.get("firefly_api_name")
            if not related_core_url or not related_api_name:
                return False
            if not firefly.find_api(str(related_core_url), str(related_api_name)):
                return False
            listeners = contract_payload.get("firefly_listeners") or []
            if not isinstance(listeners, list) or not listeners:
                return False
            for listener in listeners:
                if not isinstance(listener, dict):
                    return False
                listener_name = listener.get("name")
                if not listener_name or not firefly.find_listener(str(related_core_url), str(listener_name)):
                    return False
        return str(stored_abi_hash) == str(current_abi_hash)

    def _auto_register_dmn_firefly_after_deploy(
        self,
        env_id: str,
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        payload_detail = self._load_chainlink_deployments()
        compiled = payload_detail.get("compiled") or {}
        dmn = env.dmn_detail or (payload_detail.get("dmn_deployment") or {})
        chainlink_detail = env.chainlink_detail or (payload_detail.get("chainlink_deployment") or {})
        if not dmn.get("contractAddress"):
            return {
                "auto_registered": False,
                "message": "DMN contract address not found",
            }

        if self._dmn_firefly_registration_is_current(dmn, compiled, chainlink_detail):
            return {
                "auto_registered": False,
                "message": "DMN contract already registered to FireFly",
                "dmn_detail": dmn,
            }

        self._set_task_step(task_id, "REGISTER_FIREFLY")
        firefly_payload = self._register_dmn_firefly(env, dmn, compiled)
        if not firefly_payload:
            raise RuntimeError("DMN FireFly registration failed")

        dmn = {**dmn, **firefly_payload}
        related_payload = register_related_chainlink_contracts_to_firefly(
            env=env,
            chainlink_detail=chainlink_detail if isinstance(chainlink_detail, dict) else {},
            compiled=compiled,
            identity_flow=self._identity_orchestrator(),
            firefly_manager=self._firefly_orchestrator(),
            logger=LOG,
        )
        if related_payload:
            chainlink_detail = (
                {**chainlink_detail, **related_payload}
                if isinstance(chainlink_detail, dict)
                else related_payload
            )
        self._set_task_step(task_id, "SAVE_RESULT")
        env.dmn_detail = dmn
        env.chainlink_detail = chainlink_detail
        env.save(update_fields=["dmn_detail", "chainlink_detail"])
        return {
            "auto_registered": True,
            "message": "DMN contract registered to FireFly",
            "dmn_detail": dmn,
            "chainlink_detail": chainlink_detail,
        }

    def _run_dmn_firefly_register(
        self,
        env_id: str,
        previous_dmn_detail: dict | None = None,
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        self._set_task_step(task_id, "LOAD_DEPLOYMENT")
        payload_detail = self._load_chainlink_deployments()
        compiled = payload_detail.get("compiled") or {}
        dmn = env.dmn_detail or {}
        if not dmn:
            raise RuntimeError("DMN deployment detail not found, install chainlink/dmn first")

        chainlink_detail = env.chainlink_detail or (payload_detail.get("chainlink_deployment") or {})
        if self._dmn_firefly_registration_is_current(dmn, compiled, chainlink_detail):
            return {
                "message": "DMN contract already registered to FireFly",
                "dmn_detail": dmn,
            }

        if not dmn.get("contractAddress"):
            raise RuntimeError("DMN contract address not found")

        self._set_task_step(task_id, "REGISTER_FIREFLY")
        firefly_payload = self._register_dmn_firefly(env, dmn, compiled)
        if not firefly_payload:
            raise RuntimeError("DMN FireFly registration failed")

        dmn = {**dmn, **firefly_payload}
        related_payload = register_related_chainlink_contracts_to_firefly(
            env=env,
            chainlink_detail=chainlink_detail if isinstance(chainlink_detail, dict) else {},
            compiled=compiled,
            identity_flow=self._identity_orchestrator(),
            firefly_manager=self._firefly_orchestrator(),
            logger=LOG,
        )
        if related_payload:
            chainlink_detail = (
                {**chainlink_detail, **related_payload}
                if isinstance(chainlink_detail, dict)
                else related_payload
            )
        self._set_task_step(task_id, "SAVE_RESULT")
        env.dmn_detail = dmn
        env.chainlink_detail = chainlink_detail
        env.save(update_fields=["dmn_detail", "chainlink_detail"])
        return {
            "message": "DMN contract registered to FireFly",
            "dmn_detail": dmn,
            "chainlink_detail": chainlink_detail,
        }

    def _run_dmn_contract_redeploy(
        self,
        env_id: str,
        contract_name: str,
        task_id: str | None = None,
    ) -> dict:
        result = self._chainlink_orchestrator().redeploy_dmn_contract(
            env_id,
            contract_name=contract_name,
            task_id=task_id,
        )
        try:
            result["firefly_registration"] = self._auto_register_dmn_firefly_after_deploy(
                env_id,
                task_id=task_id,
            )
        except Exception as exc:
            LOG.warning(
                "DMNContract action=auto_register_after_redeploy_failed env=%s error=%s",
                env_id,
                exc,
            )
            result["firefly_registration_error"] = str(exc)
        return result

    def _run_oracle_task_firefly_register(
        self,
        env_id: str,
        adapter_kind: str,
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        self._set_task_step(task_id, "LOAD_DEPLOYMENT")
        payload_detail = self._load_chainlink_deployments()
        compiled = payload_detail.get("compiled") or {}
        suite = self._resolve_oracle_task_suite(env, payload_detail)
        if not suite:
            raise RuntimeError(
                "Oracle task suite has not been deployed, please run setup first"
            )

        contracts = suite.get("contracts") or {}
        suite_firefly = suite.get("firefly") or {}
        if adapter_kind == "compute":
            contract_name = "ChainlinkComputeTaskAdapter"
            contract_address = contracts.get("computeTaskAdapter")
            firefly_key = "compute_task_adapter"
            api_name = self._get_compute_task_api_name(env)
            label = "Compute task adapter"
        else:
            contract_name = "ChainlinkDataTaskAdapter"
            contract_address = contracts.get("dataTaskAdapter")
            firefly_key = "data_task_adapter"
            api_name = self._get_data_task_api_name(env)
            label = "Data task adapter"

        if not contract_address:
            raise RuntimeError(f"{label} contract address not found")

        existing = suite_firefly.get(firefly_key) or {}
        if (
            existing.get("firefly_api_name")
            and existing.get("firefly_interface_id")
            and existing.get("firefly_listeners")
        ):
            return {
                "message": f"{label} already registered to FireFly",
                "oracle_task_suite": suite,
                "adapter_kind": adapter_kind,
            }

        self._set_task_step(task_id, "REGISTER_FIREFLY")
        firefly_payload = self._register_oracle_task_adapter_firefly(
            env=env,
            compiled=compiled,
            contract_name=contract_name,
            contract_address=contract_address,
            api_name=api_name,
        )
        if not firefly_payload:
            raise RuntimeError(f"{label} FireFly registration failed")

        next_suite_firefly = {**suite_firefly, firefly_key: firefly_payload}
        next_suite = {**suite, "firefly": next_suite_firefly}
        chainlink_detail = env.chainlink_detail or {}
        if not isinstance(chainlink_detail, dict):
            chainlink_detail = {}
        chainlink_detail["oracle_task_suite"] = next_suite

        self._set_task_step(task_id, "SAVE_RESULT")
        env.chainlink_detail = chainlink_detail
        env.save(update_fields=["chainlink_detail"])
        return {
            "message": f"{label} registered to FireFly",
            "adapter_kind": adapter_kind,
            "oracle_task_suite": next_suite,
        }

    def _run_relayer_firefly_register(
        self,
        env_id: str,
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        self._set_task_step(task_id, "LOAD_DEPLOYMENT")
        payload_detail = self._load_chainlink_deployments()
        compiled = payload_detail.get("compiled") or {}
        relayer = self._resolve_relayer_deployment(env, payload_detail)
        if not relayer:
            raise RuntimeError(
                "Relayer contract has not been deployed, please run setup first"
            )

        contract = relayer.get("contract") or {}
        contract_address = contract.get("address") or relayer.get("contractAddress")
        if not contract_address:
            raise RuntimeError("Relayer contract address not found")

        existing_firefly = relayer.get("firefly") or {}
        if (
            existing_firefly.get("firefly_api_name")
            and existing_firefly.get("firefly_interface_id")
            and existing_firefly.get("firefly_listeners")
        ):
            return {
                "message": "Relayer contract already registered to FireFly",
                "relayer": relayer,
            }

        self._set_task_step(task_id, "REGISTER_FIREFLY")
        firefly_payload = self._register_oracle_task_adapter_firefly(
            env=env,
            compiled=compiled,
            contract_name="CrossChainAdapter",
            contract_address=contract_address,
            api_name=self._get_relayer_api_name(env),
        )
        if not firefly_payload:
            raise RuntimeError("Relayer contract FireFly registration failed")

        next_relayer = {**relayer, "firefly": firefly_payload}
        chainlink_detail = env.chainlink_detail or {}
        if not isinstance(chainlink_detail, dict):
            chainlink_detail = {}
        chainlink_detail["relayer"] = next_relayer

        self._set_task_step(task_id, "SAVE_RESULT")
        env.chainlink_detail = chainlink_detail
        env.save(update_fields=["chainlink_detail"])
        return {
            "message": "Relayer contract registered to FireFly",
            "relayer": next_relayer,
        }

    @action(methods=["get"], detail=True, url_path="chainlink")
    def chainlink_detail(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        sync_flag = str(request.query_params.get("sync", "")).lower() in ["1", "true", "yes", "on"]
        cluster_sync = None
        sync_error = None
        if sync_flag:
            try:
                cluster_sync = self._sync_chainlink_cluster(env, persist=True, include_jobs=True)
            except Exception as exc:
                sync_error = str(exc)
                LOG.warning("Chainlink action=sync_failed env=%s error=%s", pk, exc)

        payload = self._load_chainlink_deployments()
        chainlink = env.chainlink_detail or (payload.get("chainlink_deployment") or {})
        dmn = env.dmn_detail or (payload.get("dmn_deployment") or {})
        relayer = self._resolve_relayer_deployment(env, payload)
        contract_name = self._resolve_dmn_contract_name(dmn)

        response = {
            "chainlink_root": payload.get("chainlink_root"),
            "link_token": chainlink.get("linkToken"),
            "operator": chainlink.get("operator"),
            "ocr_contract": chainlink.get("ocrContract"),
            "dmn_job_id": chainlink.get("dmnJobId") or chainlink.get("dmnJobIds", {}).get("chainlink1"),
            "firefly": chainlink.get("firefly") or {},
            "dmn_contract": {
                "name": contract_name,
                "address": dmn.get("contractAddress"),
                "deployer": dmn.get("deployer"),
                "tx_hash": dmn.get("txHash"),
                "firefly_api_name": dmn.get("firefly_api_name"),
                "firefly_interface_id": dmn.get("firefly_interface_id"),
                "firefly_core_url": dmn.get("firefly_core_url"),
                "firefly_api_base": dmn.get("firefly_api_base"),
                "firefly_listeners": dmn.get("firefly_listeners") or [],
            },
            "chainlink_ui": os.environ.get("CHAINLINK_UI", "http://127.0.0.1:6688"),
            "cluster_sync": cluster_sync or (chainlink.get("cluster_sync") if isinstance(chainlink, dict) else None),
            "sync_error": sync_error,
            "relayer": relayer,
        }
        return Response(response, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="chainlink/sync")
    def sync_chainlink(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        include_jobs_raw = request.data.get("include_jobs", True)
        include_jobs = include_jobs_raw
        if isinstance(include_jobs_raw, str):
            include_jobs = include_jobs_raw.lower() in ["1", "true", "yes", "on"]
        else:
            include_jobs = bool(include_jobs_raw)

        snapshot = self._sync_chainlink_cluster(env, persist=True, include_jobs=include_jobs)
        return Response(
            {
                "status": env.chainlink_status,
                "cluster_sync": snapshot,
            },
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], detail=True, url_path="dmn-contract")
    def dmn_contract_detail(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        payload = self._load_chainlink_deployments()
        chainlink = env.chainlink_detail or (payload.get("chainlink_deployment") or {})
        dmn = env.dmn_detail or (payload.get("dmn_deployment") or {})
        compiled = payload.get("compiled") or {}
        contract_name = self._resolve_dmn_contract_name(dmn)
        contract_key = f"contracts/{contract_name}.sol:{contract_name}"
        abi = None
        if request.query_params.get("include_abi") in ["1", "true", "yes"]:
            abi = (compiled.get("contracts") or {}).get(contract_key, {}).get("abi")

        response = {
            "contract": {
                "name": contract_name,
                "address": dmn.get("contractAddress"),
            },
            "operator": chainlink.get("operator"),
            "link_token": chainlink.get("linkToken"),
            "dmn_job_id": chainlink.get("dmnJobId") or chainlink.get("dmnJobIds", {}).get("chainlink1"),
            "abi": abi,
            "firefly": {
                "api_name": dmn.get("firefly_api_name"),
                "interface_id": dmn.get("firefly_interface_id"),
                "core_url": dmn.get("firefly_core_url"),
                "api_base": dmn.get("firefly_api_base"),
                "listeners": dmn.get("firefly_listeners") or [],
                "registered": bool(
                    dmn.get("firefly_api_name")
                    and dmn.get("firefly_interface_id")
                    and dmn.get("firefly_listeners")
                ),
            },
            "firefly_related": chainlink.get("firefly") or {},
            "chainlink_ui": os.environ.get("CHAINLINK_UI", "http://127.0.0.1:6688"),
        }
        return Response(response, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="dmn-contract/redeploy")
    def redeploy_dmn_contract(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.chainlink_status != "STARTED":
            return Response(
                {"message": "Chainlink cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contract_name = self._resolve_dmn_contract_name(env.dmn_detail or {})
        running_task = (
            Task.objects.filter(
                target_type="EthEnvironment",
                target_id=str(env.id),
                type="DMN_CONTRACT_REDEPLOY",
                status__in=["PENDING", "RUNNING"],
            )
            .order_by("-created_at")
            .first()
        )
        if running_task:
            return Response(
                {
                    "message": "DMN contract redeploy is running",
                    "task_id": str(running_task.id),
                },
                status=status.HTTP_202_ACCEPTED,
            )

        idempotency_key = f"DMN_CONTRACT_REDEPLOY:{env.id}:{contract_name}:{uuid4()}"

        previous_dmn_detail = env.dmn_detail or {}
        task = create_task(
            task_type="DMN_CONTRACT_REDEPLOY",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"dmn_detail": previous_dmn_detail},
        )
        LOG.info(
            "DMNContract action=redeploy_task task=%s env=%s contract=%s",
            task.id,
            env.id,
            contract_name,
        )
        self._start_task(
            task,
            self._run_dmn_contract_redeploy,
            env.id,
            contract_name,
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status, "contract_name": contract_name},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="dmn-contract/register-firefly")
    def register_dmn_firefly(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready

        dmn = env.dmn_detail or {}
        payload_detail = self._load_chainlink_deployments()
        compiled = payload_detail.get("compiled") or {}
        if not dmn.get("contractAddress"):
            return Response(
                {
                    "message": (
                        "DMN contract has not been deployed for current environment, "
                        "please run DMN setup first"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        chainlink_detail = env.chainlink_detail or (payload_detail.get("chainlink_deployment") or {})
        if self._dmn_firefly_registration_is_current(dmn, compiled, chainlink_detail):
            return Response(
                {
                    "status": "STARTED",
                    "message": "DMN contract already registered to FireFly",
                    "dmn_detail": dmn,
                },
                status=status.HTTP_200_OK,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "DMN_FIREFLY_REGISTER"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        previous_dmn_detail = dmn
        task = create_task(
            task_type="DMN_FIREFLY_REGISTER",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"dmn_detail": previous_dmn_detail},
        )
        self._start_task(
            task,
            self._run_dmn_firefly_register,
            env.id,
            previous_dmn_detail,
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["get"], detail=True, url_path="data-contract")
    def data_contract_detail(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        payload = self._load_chainlink_deployments()
        suite = self._resolve_oracle_task_suite(env, payload)
        contracts = suite.get("contracts") or {}
        suite_chainlink = suite.get("chainlink") or {}
        chainlink = env.chainlink_detail or (payload.get("chainlink_deployment") or {})
        compiled = payload.get("compiled") or {}
        contract_name = "ChainlinkDataTaskAdapter"
        contract_key = f"contracts/{contract_name}.sol:{contract_name}"
        abi = None
        if request.query_params.get("include_abi") in ["1", "true", "yes"]:
            abi = (compiled.get("contracts") or {}).get(contract_key, {}).get("abi")

        firefly_payload = ((suite.get("firefly") or {}).get("data_task_adapter")) or {}
        response = {
            "contract": {
                "name": contract_name,
                "address": contracts.get("dataTaskAdapter"),
            },
            "main_router": contracts.get("mainRouter"),
            "operator": chainlink.get("operator") or suite_chainlink.get("operator"),
            "link_token": chainlink.get("linkToken") or suite_chainlink.get("linkToken"),
            "job_id": suite_chainlink.get("dataJobId"),
            "abi": abi,
            "firefly": {
                "api_name": firefly_payload.get("firefly_api_name"),
                "interface_id": firefly_payload.get("firefly_interface_id"),
                "core_url": firefly_payload.get("firefly_core_url"),
                "listeners": firefly_payload.get("firefly_listeners") or [],
                "registered": bool(
                    firefly_payload.get("firefly_api_name")
                    and firefly_payload.get("firefly_interface_id")
                    and firefly_payload.get("firefly_listeners")
                ),
            },
        }
        return Response(response, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="compute-contract")
    def compute_contract_detail(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        payload = self._load_chainlink_deployments()
        suite = self._resolve_oracle_task_suite(env, payload)
        contracts = suite.get("contracts") or {}
        suite_chainlink = suite.get("chainlink") or {}
        chainlink = env.chainlink_detail or (payload.get("chainlink_deployment") or {})
        compiled = payload.get("compiled") or {}
        contract_name = "ChainlinkComputeTaskAdapter"
        contract_key = f"contracts/{contract_name}.sol:{contract_name}"
        abi = None
        if request.query_params.get("include_abi") in ["1", "true", "yes"]:
            abi = (compiled.get("contracts") or {}).get(contract_key, {}).get("abi")

        firefly_payload = ((suite.get("firefly") or {}).get("compute_task_adapter")) or {}
        response = {
            "contract": {
                "name": contract_name,
                "address": contracts.get("computeTaskAdapter"),
            },
            "main_router": contracts.get("mainRouter"),
            "operator": chainlink.get("operator") or suite_chainlink.get("operator"),
            "link_token": chainlink.get("linkToken") or suite_chainlink.get("linkToken"),
            "job_id": suite_chainlink.get("computeJobId"),
            "abi": abi,
            "firefly": {
                "api_name": firefly_payload.get("firefly_api_name"),
                "interface_id": firefly_payload.get("firefly_interface_id"),
                "core_url": firefly_payload.get("firefly_core_url"),
                "listeners": firefly_payload.get("firefly_listeners") or [],
                "registered": bool(
                    firefly_payload.get("firefly_api_name")
                    and firefly_payload.get("firefly_interface_id")
                    and firefly_payload.get("firefly_listeners")
                ),
            },
        }
        return Response(response, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="data-contract/setup")
    def setup_data_contract(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.chainlink_status != "STARTED":
            return Response(
                {"message": "Chainlink cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suite = self._resolve_oracle_task_suite(env, self._load_chainlink_deployments())
        if ((suite.get("contracts") or {}).get("dataTaskAdapter")):
            return Response(
                {
                    "status": "STARTED",
                    "message": "Data contract already deployed",
                    "oracle_task_suite": suite,
                },
                status=status.HTTP_200_OK,
            )

        running_setup = (
            Task.objects.filter(
                target_type="EthEnvironment",
                target_id=str(env.id),
                type__in=["DATA_CONTRACT_SETUP", "COMPUTE_CONTRACT_SETUP"],
                status__in=["PENDING", "RUNNING"],
            )
            .order_by("-created_at")
            .first()
        )
        if running_setup:
            return Response(
                {"message": "Oracle task suite setup is running", "task_id": str(running_setup.id)},
                status=status.HTTP_202_ACCEPTED,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "DATA_CONTRACT_SETUP"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        task = create_task(
            task_type="DATA_CONTRACT_SETUP",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"chainlink_detail": env.chainlink_detail},
        )
        self._start_task(
            task,
            self._run_oracle_task_suite_setup,
            env.id,
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="compute-contract/setup")
    def setup_compute_contract(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.chainlink_status != "STARTED":
            return Response(
                {"message": "Chainlink cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suite = self._resolve_oracle_task_suite(env, self._load_chainlink_deployments())
        if ((suite.get("contracts") or {}).get("computeTaskAdapter")):
            return Response(
                {
                    "status": "STARTED",
                    "message": "Compute contract already deployed",
                    "oracle_task_suite": suite,
                },
                status=status.HTTP_200_OK,
            )

        running_setup = (
            Task.objects.filter(
                target_type="EthEnvironment",
                target_id=str(env.id),
                type__in=["DATA_CONTRACT_SETUP", "COMPUTE_CONTRACT_SETUP"],
                status__in=["PENDING", "RUNNING"],
            )
            .order_by("-created_at")
            .first()
        )
        if running_setup:
            return Response(
                {"message": "Oracle task suite setup is running", "task_id": str(running_setup.id)},
                status=status.HTTP_202_ACCEPTED,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "COMPUTE_CONTRACT_SETUP"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        task = create_task(
            task_type="COMPUTE_CONTRACT_SETUP",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"chainlink_detail": env.chainlink_detail},
        )
        self._start_task(
            task,
            self._run_oracle_task_suite_setup,
            env.id,
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="data-contract/register-firefly")
    def register_data_contract_firefly(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.firefly_status != "STARTED":
            return Response(
                {"message": "FireFly cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suite = self._resolve_oracle_task_suite(env, self._load_chainlink_deployments())
        contracts = suite.get("contracts") or {}
        if not contracts.get("dataTaskAdapter"):
            return Response(
                {"message": "Data contract has not been deployed, please run setup first"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        firefly_payload = ((suite.get("firefly") or {}).get("data_task_adapter")) or {}
        if (
            firefly_payload.get("firefly_api_name")
            and firefly_payload.get("firefly_interface_id")
            and firefly_payload.get("firefly_listeners")
        ):
            return Response(
                {
                    "status": "STARTED",
                    "message": "Data contract already registered to FireFly",
                    "oracle_task_suite": suite,
                },
                status=status.HTTP_200_OK,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "DATA_CONTRACT_FIREFLY_REGISTER"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        task = create_task(
            task_type="DATA_CONTRACT_FIREFLY_REGISTER",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"chainlink_detail": env.chainlink_detail},
        )
        self._start_task(
            task,
            self._run_oracle_task_firefly_register,
            env.id,
            "data",
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="compute-contract/register-firefly")
    def register_compute_contract_firefly(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.firefly_status != "STARTED":
            return Response(
                {"message": "FireFly cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suite = self._resolve_oracle_task_suite(env, self._load_chainlink_deployments())
        contracts = suite.get("contracts") or {}
        if not contracts.get("computeTaskAdapter"):
            return Response(
                {"message": "Compute contract has not been deployed, please run setup first"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        firefly_payload = ((suite.get("firefly") or {}).get("compute_task_adapter")) or {}
        if (
            firefly_payload.get("firefly_api_name")
            and firefly_payload.get("firefly_interface_id")
            and firefly_payload.get("firefly_listeners")
        ):
            return Response(
                {
                    "status": "STARTED",
                    "message": "Compute contract already registered to FireFly",
                    "oracle_task_suite": suite,
                },
                status=status.HTTP_200_OK,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "COMPUTE_CONTRACT_FIREFLY_REGISTER"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        task = create_task(
            task_type="COMPUTE_CONTRACT_FIREFLY_REGISTER",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"chainlink_detail": env.chainlink_detail},
        )
        self._start_task(
            task,
            self._run_oracle_task_firefly_register,
            env.id,
            "compute",
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["get"], detail=True, url_path="relayer-contract")
    def relayer_contract_detail(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        payload = self._load_chainlink_deployments()
        relayer = self._resolve_relayer_deployment(env, payload)
        compiled = payload.get("compiled") or {}
        contract_name = "CrossChainAdapter"
        contract = relayer.get("contract") or {}
        contract_address = contract.get("address") or relayer.get("contractAddress")
        abi = None
        if request.query_params.get("include_abi") in ["1", "true", "yes"]:
            contract_key = f"contracts/{contract_name}.sol:{contract_name}"
            abi = (compiled.get("contracts") or {}).get(contract_key, {}).get("abi")

        firefly_payload = relayer.get("firefly") or {}
        node_status = self._chainlink_orchestrator().relayer_node_status()
        response = {
            "contract": {
                "name": contract_name,
                "address": contract_address,
                "tx_hash": contract.get("txHash") or relayer.get("tx_hash"),
            },
            "relayers": relayer.get("relayers") or [],
            "threshold": relayer.get("threshold"),
            "abi": abi,
            "firefly": {
                "api_name": firefly_payload.get("firefly_api_name"),
                "interface_id": firefly_payload.get("firefly_interface_id"),
                "core_url": firefly_payload.get("firefly_core_url"),
                "listeners": firefly_payload.get("firefly_listeners") or [],
                "registered": bool(
                    firefly_payload.get("firefly_api_name")
                    and firefly_payload.get("firefly_interface_id")
                    and firefly_payload.get("firefly_listeners")
                ),
            },
            "node": node_status,
        }
        return Response(response, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="relayer-contract/setup")
    def setup_relayer_contract(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.chainlink_status != "STARTED":
            return Response(
                {"message": "Chainlink cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        relayer = self._resolve_relayer_deployment(env, self._load_chainlink_deployments())
        contract = relayer.get("contract") or {}
        contract_address = contract.get("address") or relayer.get("contractAddress")
        if contract_address:
            return Response(
                {
                    "status": "STARTED",
                    "message": "Relayer contract already deployed",
                    "relayer": relayer,
                },
                status=status.HTTP_200_OK,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "RELAYER_CONTRACT_SETUP"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        task = create_task(
            task_type="RELAYER_CONTRACT_SETUP",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"chainlink_detail": env.chainlink_detail},
        )
        self._start_task(
            task,
            self._run_relayer_setup,
            env.id,
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="relayer-contract/register-firefly")
    def register_relayer_contract_firefly(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.firefly_status != "STARTED":
            return Response(
                {"message": "FireFly cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        relayer = self._resolve_relayer_deployment(env, self._load_chainlink_deployments())
        contract = relayer.get("contract") or {}
        contract_address = contract.get("address") or relayer.get("contractAddress")
        if not contract_address:
            return Response(
                {
                    "message": (
                        "Relayer contract has not been deployed for current environment, "
                        "please run relayer setup first"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        firefly_payload = relayer.get("firefly") or {}
        if (
            firefly_payload.get("firefly_api_name")
            and firefly_payload.get("firefly_interface_id")
            and firefly_payload.get("firefly_listeners")
        ):
            return Response(
                {
                    "status": "STARTED",
                    "message": "Relayer contract already registered to FireFly",
                    "relayer": relayer,
                },
                status=status.HTTP_200_OK,
            )

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "RELAYER_CONTRACT_FIREFLY_REGISTER"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        task = create_task(
            task_type="RELAYER_CONTRACT_FIREFLY_REGISTER",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={"chainlink_detail": env.chainlink_detail},
        )
        self._start_task(
            task,
            self._run_relayer_firefly_register,
            env.id,
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["get"], detail=True, url_path="relayer-node")
    def relayer_node_status(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        return Response(
            self._chainlink_orchestrator().relayer_node_status(),
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True, url_path="relayer-node/(?P<command>[^/.]+)")
    def relayer_node_control(self, request, pk=None, command=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        try:
            payload = self._chainlink_orchestrator().control_relayer_node(command or "")
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"message": f"Relayer node control failed: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payload, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="chainlink/install")
    def install_chainlink(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            LOG.warning("Chainlink action=install_missing_env env=%s", pk)
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            LOG.warning(
                "Chainlink action=install_rejected env=%s status=%s",
                env.id,
                env.status,
            )
            return not_ready

        mode = (request.data.get("mode") or "lite").lower()
        if mode not in ["lite", "full"]:
            mode = "lite"

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "CHAINLINK_INSTALL", mode
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        LOG.info(
            "Chainlink action=install_request env=%s mode=%s user=%s",
            env.id,
            mode,
            getattr(request.user, "id", None),
        )

        task, _ = create_task_with_status_transition(
            task_type="CHAINLINK_INSTALL",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            target_obj=env,
            status_field="chainlink_status",
            pending_value="SETTINGUP",
        )
        LOG.info(
            "Chainlink action=install_task task=%s env=%s mode=%s status=%s",
            task.id,
            env.id,
            mode,
            task.status,
        )

        self._start_task(
            task,
            self._run_chainlink_setup,
            env.id,
            mode,
            str(task.id),
        )
        return Response(
            {"task_id": str(task.id), "status": task.status, "mode": mode},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="chainlink/create-job")
    def create_chainlink_job(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            LOG.warning("Chainlink action=create_job_missing_env env=%s", pk)
            return error_response
        not_ready = self._require_started_or_activated(env)
        if not_ready:
            return not_ready
        if env.chainlink_status != "STARTED":
            return Response(
                {"message": "Chainlink cluster has not been started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recreate = bool(request.data.get("recreate"))
        job_kind_raw = request.data.get("job_kind") or request.data.get("jobKind") or "dmn"
        job_kind = (
            "datasource"
            if str(job_kind_raw).lower() in ["datasource", "data_source", "source"]
            else "dmn"
        )
        data_source_url = request.data.get("data_source_url") or request.data.get("dataSourceUrl")
        data_source_method = (request.data.get("data_source_method") or request.data.get("dataSourceMethod") or "GET").upper()
        if data_source_method not in ["GET", "POST"]:
            return Response(
                {"message": "data_source_method must be GET or POST"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if data_source_url and not str(data_source_url).startswith(("http://", "https://")):
            return Response(
                {"message": "data_source_url must start with http:// or https://"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sync_onchain_raw = request.data.get("sync_onchain")
        if sync_onchain_raw is None:
            sync_onchain = job_kind == "dmn"
        elif isinstance(sync_onchain_raw, str):
            sync_onchain = sync_onchain_raw.lower() not in ["0", "false", "no"]
        else:
            sync_onchain = bool(sync_onchain_raw)
        external_job_id = request.data.get("external_job_id") or request.data.get("externalJobId")

        mode_key = (
            f"kind={job_kind}:recreate={int(recreate)}:sync={int(sync_onchain)}:"
            f"job={external_job_id or ''}:url={data_source_url or ''}:method={data_source_method}"
        )
        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "CHAINLINK_JOB_CREATE", mode_key
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        task = create_task(
            task_type="CHAINLINK_JOB_CREATE",
            target_type="EthEnvironment",
            target_id=str(env.id),
            idempotency_key=idempotency_key,
            rollback_info={
                "chainlink_detail": env.chainlink_detail,
                "dmn_detail": env.dmn_detail,
            },
        )
        self._start_task(
            task,
            self._run_chainlink_create_job,
            env.id,
            recreate,
            external_job_id,
            sync_onchain,
            job_kind,
            data_source_url,
            data_source_method,
            str(task.id),
        )
        return Response(
            {
                "task_id": str(task.id),
                "status": task.status,
                "job_kind": job_kind,
                "recreate": recreate,
                "sync_onchain": sync_onchain,
                "external_job_id": external_job_id,
                "data_source_url": data_source_url,
                "data_source_method": data_source_method,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["get"], detail=True, url_path="account-check")
    def account_check(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        try:
            result = self._check_system_account_available(env)
        except Exception as exc:
            LOG.warning("Eth account check failed env=%s error=%s", pk, exc)
            return Response(
                {"message": "account check failed", "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        http_status = (
            status.HTTP_200_OK
            if result.get("has_expected_account") and result.get("unlock_ok")
            else status.HTTP_409_CONFLICT
        )
        return Response(result, status=http_status)

    @action(methods=["post"], detail=True, url_path="init")
    @timeitwithname("InitEth")
    def init(self, request, pk=None, *args, **kwargs):
        """
        初始化EthEnvironment
        """

        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "CREATED":
            return Response(
                {"message": "EthEnvironment has been initialized"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consortium = env.consortium

        system_org = LoleidoOrganization.objects.create(
            name=consortium.name + env.name + "-system",
        )

        membership = Membership.objects.create(
            name=env.name + "-system",
            loleido_organization=system_org,
            consortium=consortium,
        )

        agent = Agent.objects.create(   # agent需要？
            name="system-agent",
            type=DEFAULT_AGENT["type"],
            urls=DEFAULT_AGENT["urls"],
            status="active",
        )

        resource_set = ResourceSet.objects.create(
            name=membership.name, eth_environment=env, membership=membership, agent=agent
        )
        
        ethereum_resource_set = EthereumResourceSet.objects.create(
            resource_set=resource_set,
            org_type=1,
            name=membership.name + ".org" + ".com",
            # msp=membership.name + ".org" + ".com" + "OrdererMSP",
        )
        
        headers = request.headers
        node_name = "system-geth-node"
        response = post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/eth/node_create",
            data={
                "name": node_name,
                "type": EthNodeType.System.value
                },
            headers={"Authorization": headers["Authorization"]},
        )

        # Extract and save the enode from the response
        if response.status_code == 202:
            try:
                response_data = response.json()
                result = response_data.get("res", {}).get("result", {})
                if "enode" in result:
                    # Save the enode to the environment for later use
                    env.metadata = env.metadata or {}
                    env.metadata["sys_enode"] = result["enode"]
                    LOG.info(f"System node enode saved: {result['enode']}")
            except Exception as e:
                LOG.warning(f"Failed to extract enode from response: {e}")

        env.status = "INITIALIZED"
        env.save()

        # Validate the preconfigured system account right after network bootstrap.
        try:
            account_check = self._check_system_account_available(env)
            LOG.info(
                "Eth account check env=%s has_expected=%s unlock_ok=%s rpc=%s",
                env.id,
                account_check.get("has_expected_account"),
                account_check.get("unlock_ok"),
                account_check.get("rpc_url"),
            )
            if not account_check.get("has_expected_account"):
                LOG.warning(
                    "Eth account check env=%s expected account missing expected=%s accounts=%s",
                    env.id,
                    account_check.get("expected_account"),
                    account_check.get("accounts"),
                )
        except Exception as exc:
            LOG.warning("Eth account check env=%s failed: %s", env.id, exc)

        return Response(status=status.HTTP_201_CREATED)

    @parser_classes([MultiPartParser, FormParser, JSONParser])
    @action(methods=["post"], detail=True, url_path="identity-contract/install")
    def install_identity_contract(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(
            env,
            message="EthEnvironment has not been activated or has started",
        )
        if not_ready:
            return not_ready

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "IDENTITY_CONTRACT_INSTALL"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]
        compiler_version = str(request.data.get("compiler_version") or "").strip() or None
        contract_name = str(request.data.get("contract_name") or "").strip() or None
        if contract_name and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", contract_name):
            return Response(
                {"message": "Invalid contract_name. Use letters, numbers and underscores, and start with a letter or underscore."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        archive = request.FILES.get("archive") or request.FILES.get("file")
        archive_path = None

        if archive:
            archive_name = getattr(archive, "name", "").lower()
            allowed_suffixes = (".zip", ".tar", ".tgz", ".tar.gz")
            if not archive_name.endswith(allowed_suffixes):
                return Response(
                    {"message": "Unsupported archive format. Use zip/tar/tgz source bundle."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            archive_path = self._store_identity_archive_upload(archive)

        deployment, _ = IdentityDeployment.objects.get_or_create(
            eth_environment=env
        )
        if deployment.status == "STARTED" and deployment.contract_address:
            if archive_path and os.path.exists(archive_path):
                try:
                    os.remove(archive_path)
                except Exception:
                    LOG.warning("IdentityContract upload cleanup failed env=%s path=%s", env.id, archive_path)
            LOG.info("IdentityContract action=already_deployed env=%s", env.id)
            return Response(
                {
                    "status": deployment.status,
                    "contract_address": deployment.contract_address,
                    "transaction_hash": deployment.deployment_tx_hash,
                    "deployment_id": deployment.deployment_id,
                },
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            previous_status = env.identity_contract_status
            env.identity_contract_status = "PENDING"
            env.save(update_fields=["identity_contract_status"])
            deployment.status = "PENDING"
            deployment.error = None
            deployment.save(update_fields=["status", "error", "updated_at"])
            task = create_task(
                task_type="IDENTITY_CONTRACT_INSTALL",
                target_type="EthEnvironment",
                target_id=str(env.id),
                idempotency_key=idempotency_key,
                rollback_info={"identity_contract_status": previous_status},
            )
        LOG.info("IdentityContract action=install_task task=%s env=%s", task.id, env.id)

        identity = self._identity_orchestrator()
        self._start_task(
            task,
            identity.deploy_identity_contract,
            env.id,
            source_archive_path=archive_path,
            compiler_version=compiler_version,
            contract_name=contract_name,
        )

        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="identity-contract/redeploy")
    def redeploy_identity_contract(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        idempotent = self._ensure_idempotent_task(
            request, str(env.id), "IDENTITY_CONTRACT_REDEPLOY"
        )
        if idempotent.get("response"):
            return idempotent["response"]
        idempotency_key = idempotent["idempotency_key"]

        with transaction.atomic():
            previous_status = env.identity_contract_status
            env.identity_contract_status = "PENDING"
            env.save(update_fields=["identity_contract_status"])
            deployment, _ = IdentityDeployment.objects.get_or_create(
                eth_environment=env
            )
            deployment.status = "PENDING"
            deployment.error = None
            deployment.save(update_fields=["status", "error", "updated_at"])
            task = create_task(
                task_type="IDENTITY_CONTRACT_REDEPLOY",
                target_type="EthEnvironment",
                target_id=str(env.id),
                idempotency_key=idempotency_key,
                rollback_info={"identity_contract_status": previous_status},
            )
        LOG.info("IdentityContract action=redeploy_task task=%s env=%s", task.id, env.id)
        identity = self._identity_orchestrator()
        self._start_task(task, identity.redeploy_and_sync, env.id)
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["get"], detail=True, url_path="identity-contract")
    def identity_contract_detail(self, request, pk=None, *args, **kwargs):
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response

        deployment = IdentityDeployment.objects.filter(
            eth_environment=env
        ).first()
        identity = self._identity_orchestrator()
        firefly_core_url = None
        try:
            firefly_core_url = identity.get_firefly_core_url(env)
        except Exception:
            firefly_core_url = None
        abi = None
        if request.query_params.get("include_abi") in ["1", "true", "yes"]:
            abi = identity.load_identity_abi()

        response = {
            "environment_id": str(env.id),
            "status": env.identity_contract_status,
            "deployment": None,
            "abi": abi,
            "firefly_core_url": firefly_core_url,
        }
        if deployment:
            api_name = deployment.api_name or deployment.contract_name or "IdentityRegistry"
            api_base = None
            if deployment.api_address:
                api_base = deployment.api_address
            elif firefly_core_url:
                api_base = (
                    f"http://{firefly_core_url}/api/v1/namespaces/default/apis/{api_name}"
                )
            response["deployment"] = {
                "id": str(deployment.id),
                "contract_name": deployment.contract_name,
                "contract_address": deployment.contract_address,
                "deployment_tx_hash": deployment.deployment_tx_hash,
                "deployment_id": deployment.deployment_id,
                "interface_id": deployment.interface_id,
                "api_id": deployment.api_id,
                "api_name": api_name,
                "api_address": deployment.api_address,
                "firefly_listeners": deployment.firefly_listeners or [],
                "status": deployment.status,
                "error": deployment.error,
                "updated_at": deployment.updated_at,
                "firefly_contract_base": (
                    f"http://{firefly_core_url}/api/v1/namespaces/default/contracts/"
                    f"{deployment.contract_address}"
                )
                if firefly_core_url and deployment.contract_address
                else None,
                "firefly_api_base": api_base,
            }
        artifact_meta = identity.flow._load_identity_artifact_meta()
        if artifact_meta:
            response["artifacts"] = artifact_meta
        return Response(response, status=status.HTTP_200_OK)


    @action(methods=["post"], detail=True, url_path="join")
    @timeitwithname("JoinEthereum")
    def join(self, request, pk=None, *args, **kwargs):
        try:
            membership_id = request.data.get("membership_id", None)
            LOG.info(f"Join request - environment: {pk}, membership: {membership_id}")

            try:
                membership = Membership.objects.get(pk=membership_id)
            except Membership.DoesNotExist:
                LOG.error(f"Membership {membership_id} not found")
                return Response(
                    {"message": "Membership not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            try:
                environment = EthEnvironment.objects.get(pk=pk)
            except EthEnvironment.DoesNotExist:
                LOG.error(f"Environment {pk} not found")
                return Response(
                    {"message": "Environment not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            if environment.status != "INITIALIZED":
                LOG.warning(f"Environment {pk} status is {environment.status}, expected INITIALIZED")
                return Response(
                    {"message": "Ethereum Environment has not been initialized or has started"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 创建资源组
            org = membership.loleido_organization
            agent = Agent.objects.create(
                name=f"{membership.name}-agent",
                type=DEFAULT_AGENT["type"],
                urls=DEFAULT_AGENT["urls"],
                status="active",
                organization=org,
            )
            LOG.info(f"Created agent: {agent.id}")

            resource_set = ResourceSet.objects.create(
                name=membership.name,
                eth_environment=environment,
                membership=membership,
                agent=agent,
            )
            LOG.info(f"Created resource_set: {resource_set.id}")

            ethereum_resource_set = EthereumResourceSet.objects.create(
                resource_set=resource_set,
                org_type=0,  # 0 表示 UserOrg
                name=membership.name + ".org" + ".com",
            )
            LOG.info(f"Created ethereum_resource_set: {ethereum_resource_set.id}")

            # Get system node enode from the system resource set
            # Find the system resource set (org_type=1)
            system_resource_sets = environment.resource_sets.filter(
                ethereum_sub_resource_set__org_type=1
            )
            if not system_resource_sets.exists():
                LOG.error(f"No system resource set found for environment {pk}")
                return Response(
                    {"message": "System resource set not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            system_resource_set = system_resource_sets.first()
            LOG.info(f"Found system resource set: {system_resource_set.id}")

            # Get the system node
            system_nodes = EthNode.objects.filter(
                fabric_resource_set__resource_set=system_resource_set
            )
            if not system_nodes.exists():
                LOG.error(f"No system node found in resource set {system_resource_set.id}")
                return Response(
                    {"message": "System node not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            system_node = system_nodes.first()
            LOG.info(f"Found system node: {system_node.id}, name: {system_node.name}")

            if not system_node.sys_enode:
                LOG.error(f"System node {system_node.id} has no enode")
                return Response(
                    {"message": "System node enode not available yet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sys_enode = system_node.sys_enode
            LOG.info(f"Using system node enode: {sys_enode}")

            headers = request.headers
            response = post(
                f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/eth/node_create",
                data={
                    "name": ethereum_resource_set.name,
                    "type": EthNodeType.Organization.value,
                    "sys_enode": sys_enode,
                },
                headers={"Authorization": headers["Authorization"]},
            )
            LOG.info(f"Node create response status: {response.status_code}")

            if response.status_code >= 400:
                LOG.error(f"Node create failed: {response.text}")
                return Response(
                    {"message": f"Failed to create organization node: {response.text}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(status=status.HTTP_201_CREATED)

        except Exception as e:
            LOG.exception(f"Unexpected error in join: {e}")
            return Response(
                {"message": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(methods=["post"], detail=True, url_path="start")
    @timeitwithname("StartEth")
    def start(self, request, pk=None, *args, **kwargs):
        """
        启动EthEnvironment - Only changes environment status.
        This is an idempotent state transition and must not downgrade an activated env.
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status == "ACTIVATED":
            return Response(
                {"message": "Environment already activated"},
                status=status.HTTP_200_OK,
            )

        if env.status == "STARTED":
            return Response(
                {"message": "Environment already started"},
                status=status.HTTP_200_OK,
            )

        if env.status != "INITIALIZED":
            return Response(
                {"message": "EthEnvironment has not been initialized"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        env.status = "STARTED"
        env.save()

        return Response(
            {"message": "Environment started successfully"},
            status=status.HTTP_201_CREATED
        )

    @action(methods=["post"], detail=True, url_path="activate")
    @timeitwithname("ActivateEth")
    def activate(self, request, pk=None, *args, **kwargs):
        """
        激活EthEnvironment - Only changes environment status.
        This is the logical "ready for ecosystem deployment" marker after start.
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status == "ACTIVATED":
            return Response(
                {"message": "Environment already activated"},
                status=status.HTTP_200_OK,
            )

        if env.status not in ["INITIALIZED", "STARTED"]:
            return Response(
                {"message": "EthEnvironment has not been initialized or started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        env.status = "ACTIVATED"
        env.save()

        return Response(
            {"message": "Environment activated successfully"},
            status=status.HTTP_201_CREATED
        )

    @action(methods=["post"], detail=True, url_path="install_firefly")
    def install_firefly(self, request, pk=None, *args, **kwargs):
        """
        安装Firefly
        """
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(
            env,
            message="EthEnvironment has not been activated or has started",
        )
        if not_ready:
            return not_ready

        org_id = request.data.get("org_id")
        return self._enqueue_eth_chaincode_install(
            request,
            env,
            task_type="ETH_FIREFLY_INSTALL",
            status_field="firefly_status",
            file_path=FABRIC_CONFIG + "/firefly-go.zip",
            chaincode_name="Firefly",
            org_id=org_id,
        )

    @action(methods=["post"], detail=True, url_path="install_oracle")
    def install_oracle(self, request, pk=None, *args, **kwargs):
        """
        安装Oracle
        """
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(
            env,
            message="EthEnvironment has not been activated or has started",
        )
        if not_ready:
            return not_ready

        org_id = request.data.get("org_id")
        return self._enqueue_eth_chaincode_install(
            request,
            env,
            task_type="ETH_ORACLE_INSTALL",
            status_field="Oracle_status",
            file_path=ORACLE_CONTRACT_PATH + "/oracle-go.zip",
            chaincode_name="Oracle",
            org_id=org_id,
        )

    @action(methods=["post"], detail=True, url_path="install_dmn_engine")
    def install_dmn_engine(self, request, pk=None, *args, **kwargs):
        """
        启动DMN Engine: 部署合约
        """
        env, error_response = self._get_eth_env_or_404(pk)
        if error_response:
            return error_response
        not_ready = self._require_started_or_activated(
            env,
            message="EthEnvironment has not been activated or has started",
        )
        if not_ready:
            return not_ready

        org_id = request.data.get("org_id")
        return self._enqueue_eth_chaincode_install(
            request,
            env,
            task_type="ETH_DMN_INSTALL",
            status_field="DMN_status",
            file_path=DMN_CONTRACT_PATH + "/dmn-engine.zip",
            chaincode_name="DMNEngine",
            org_id=org_id,
            language="java",
        )

    @action(methods=["get"], detail=False, url_path="requestOracleFFI")
    def requestOracleFFI(self, request, pk=None, *args, **kwargs):
        """
        请求Oracle FFI
        """
        with open(ORACLE_CONTRACT_PATH + "/oracleFFI.json", "r") as f:
            ffiContent = f.read()

        response = {"ffiContent": ffiContent}

        return Response(response, status=status.HTTP_200_OK)
