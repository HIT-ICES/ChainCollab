import json
import logging
import os
import shutil
import time
from threading import Thread
from requests import post
import requests
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.common.enums import EthNodeType, FabricNodeType

from .serializers import EnvironmentSerializer, EthEnvironmentSerializer
from rest_framework.decorators import action

from api.models import (
    Consortium,
    Environment,
    EthEnvironment,
    EthereumResourceSet,
    EthNode,
    ResourceSet,
    Agent,
    Membership,
    FabricResourceSet,
    LoleidoOrganization,
    Firefly,
    Task,
    IdentityDeployment,
    EthereumIdentity,
)
from api.config import (
    DEFAULT_AGENT,
    DEFAULT_CHANNEL_NAME,
    FABRIC_CONFIG,
    CURRENT_IP,
    ORACLE_CONTRACT_PATH,
    DMN_CONTRACT_PATH,
    ETHEREUM_CONTRACT_STORE,
)
from api.lib.ethereum.solc_compiler import SolidityCompiler
from api.lib.ethereum.convert_contract import extract_contract_info
from api.utils.test_time import timeitwithname
from .utils import (
    packageChaincodeForEnv,
    installChaincodeForEnv,
    approveChaincodeForEnv,
    commmitChaincodeForEnv,
)

LOG = logging.getLogger(__name__)


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

        if env.status != "ACTIVATED":
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers

        post(
            f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/fireflys/init",
            headers={"Authorization": headers["Authorization"]},
        )

        post(
            f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/fireflys/start",
            headers={"Authorization": headers["Authorization"]},
        )
        env.firefly_status = "STARTED"
        env.save()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="install_firefly")
    def install_firefly(self, request, pk=None, *args, **kwargs):
        """
        安装Firefly
        """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "ACTIVATED":
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers
        org_id = request.data.get("org_id")
        chaincode_id = packageChaincodeForEnv(
            env_id=env.id,
            file_path=FABRIC_CONFIG + "/firefly-go.zip",
            chaincode_name="Firefly",
            version="1.0",
            org_id=org_id,
            auth=headers["Authorization"],
        )

        installChaincodeForEnv(
            env_id=env.id,
            chaincode_id=chaincode_id,
            auth=headers["Authorization"],
        )

        approveChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Firefly",
            auth=headers["Authorization"],
        )

        commmitChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Firefly",
            auth=headers["Authorization"],
        )

        env.firefly_status = "CHAINCODEINSTALLED"
        env.save()
        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="install_oracle")
    def install_oracle(self, request, pk=None, *args, **kwargs):
        """ """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "ACTIVATED":
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers
        org_id = request.data.get("org_id")
        chaincode_id = packageChaincodeForEnv(
            env_id=env.id,
            file_path=ORACLE_CONTRACT_PATH + "/oracle-go.zip",
            chaincode_name="Oracle",
            version="1.0",
            org_id=org_id,
            auth=headers["Authorization"],
        )

        installChaincodeForEnv(
            env_id=env.id,
            chaincode_id=chaincode_id,
            auth=headers["Authorization"],
        )

        approveChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Oracle",
            auth=headers["Authorization"],
        )

        commmitChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Oracle",
            auth=headers["Authorization"],
        )

        env.Oracle_status = "CHAINCODEINSTALLED"
        env.save()

        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="install_dmn_engine")
    def install_dmn_engine(self, request, pk=None, *args, **kwargs):
        """
        启动DMN Engine: 部署合约
        """
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "ACTIVATED":
            return Response(
                {"message": "Environment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers
        org_id = request.data.get("org_id")

        chaincode_id = packageChaincodeForEnv(
            env_id=env.id,
            file_path=DMN_CONTRACT_PATH + "/dmn-engine.zip",
            chaincode_name="DMNEngine",
            version="1.0",
            org_id=org_id,
            auth=headers["Authorization"],
            language="java",
        )

        installChaincodeForEnv(
            env_id=env.id,
            chaincode_id=chaincode_id,
            auth=headers["Authorization"],
        )

        approveChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="DMNEngine",
            auth=headers["Authorization"],
        )

        commmitChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="DMNEngine",
            auth=headers["Authorization"],
        )

        env.DMN_status = "CHAINCODEINSTALLED"
        env.save()

        return Response(status=status.HTTP_200_OK)

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

    def _start_task(self, task, handler, *args, **kwargs):
        def runner():
            task.status = "RUNNING"
            task.save(update_fields=["status", "updated_at"])
            LOG.info("Task %s started (%s)", task.id, task.type)
            try:
                result = handler(*args, **kwargs)
                task.status = "SUCCESS"
                task.result = result
                task.error = None
                LOG.info("Task %s finished (%s)", task.id, task.type)
            except Exception as exc:
                LOG.exception("Task %s failed", task.id)
                task.status = "FAILED"
                task.error = str(exc)
            task.save(update_fields=["status", "result", "error", "updated_at"])

        thread = Thread(target=runner, daemon=True)
        thread.start()

    def _resolve_identity_artifacts(self):
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../../..")
        )
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        os.makedirs(contract_dir, exist_ok=True)
        abi_path = os.path.join(contract_dir, "IdentityRegistry.abi")
        bin_path = os.path.join(contract_dir, "IdentityRegistry.bin")
        sol_copy_path = os.path.join(contract_dir, "IdentityRegistry.sol")

        if not os.path.exists(sol_copy_path):
            source_path = os.path.join(
                repo_root,
                "src",
                "geth_identity_contract",
                "contracts",
                "IdentityRegistry.sol",
            )
            if not os.path.exists(source_path):
                raise FileNotFoundError(
                    "IdentityRegistry.sol not found under geth_identity_contract/contracts"
                )
            shutil.copyfile(source_path, sol_copy_path)

        if not os.path.exists(abi_path) or not os.path.exists(bin_path):
            compiler = SolidityCompiler()
            is_installed, version_or_error = compiler.check_installation()
            if not is_installed:
                raise Exception(
                    f"Solidity compiler not available: {version_or_error}"
                )
            output_json_path = os.path.join(contract_dir, "IdentityRegistry.json")
            return_code, compiled_data, error_msg = compiler.compile_contract(
                sol_copy_path, output_json_path
            )
            if return_code != 0:
                raise Exception(f"Compilation failed: {error_msg}")
            contract_info = extract_contract_info(
                compiled_data, contract_name="IdentityRegistry"
            )
            with open(abi_path, "w") as abi_file:
                json.dump(contract_info["definition"], abi_file, indent=2)
            with open(bin_path, "w") as bin_file:
                bin_file.write(contract_info["contract"])
        with open(abi_path, "r") as abi_file:
            abi = json.load(abi_file)
        with open(bin_path, "r") as bin_file:
            bytecode = bin_file.read().strip()
        if not bytecode:
            raise ValueError("IdentityRegistry bytecode is empty")
        return abi, bytecode

    def _looks_like_eth_address(self, value: str | None) -> bool:
        if not value or not isinstance(value, str):
            return False
        return value.startswith("0x") and len(value) == 42

    def _fetch_firefly_org_admin_address(self, firefly: Firefly) -> str | None:
        try:
            response = requests.get(
                f"http://{firefly.core_url}/api/v1/identities",
                params={"fetchverifiers": "true"},
                timeout=30,
            )
            LOG.info(
                "FireFly identities request org=%s status=%s",
                firefly.org_name,
                response.status_code,
            )
            if response.status_code not in [200, 202]:
                LOG.warning(
                    "FireFly identities query failed org=%s status=%s",
                    firefly.org_name,
                    response.status_code,
                )
                return None
            payload = response.json()
        except Exception as exc:
            LOG.warning(
                "FireFly identities query failed org=%s err=%s",
                firefly.org_name,
                exc,
            )
            return None
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("identities") or payload.get("items") or []
        else:
            items = []
        if not isinstance(items, list):
            return None
        org_identities = [item for item in items if item.get("type") == "org"]
        LOG.info(
            "FireFly identities fetched org=%s total=%s org_total=%s",
            firefly.org_name,
            len(items),
            len(org_identities),
        )
        for identity in items:
            if identity.get("type") != "org":
                continue
            if identity.get("name") != firefly.org_name:
                continue
            verifiers = identity.get("verifiers") or []
            for verifier in verifiers:
                if verifier.get("type") == "ethereum_address":
                    value = verifier.get("value")
                    if self._looks_like_eth_address(value):
                        return value
        return None

    def _abi_type_to_schema(self, abi_type: str) -> dict:
        if abi_type.endswith("]"):
            base = abi_type[: abi_type.index("[")]
            return {
                "type": "array",
                "details": {"type": abi_type},
                "items": self._abi_type_to_schema(base),
            }
        if abi_type.startswith("uint") or abi_type.startswith("int"):
            return {
                "type": "integer",
                "details": {"type": abi_type},
            }
        if abi_type == "bool":
            return {"type": "boolean", "details": {"type": abi_type}}
        if abi_type == "address":
            return {"type": "string", "details": {"type": abi_type}}
        if abi_type.startswith("bytes"):
            return {"type": "string", "details": {"type": abi_type}}
        if abi_type == "string":
            return {"type": "string", "details": {"type": abi_type}}
        return {"type": "string", "details": {"type": abi_type}}

    def _build_identity_ffi(self, abi: list) -> dict:
        methods = []
        for entry in abi:
            if entry.get("type") != "function":
                continue
            params = [
                {
                    "name": param.get("name") or f"arg{idx}",
                    "schema": self._abi_type_to_schema(param.get("type", "string")),
                }
                for idx, param in enumerate(entry.get("inputs", []))
            ]
            returns = [
                {
                    "name": output.get("name") or f"ret{idx}",
                    "schema": self._abi_type_to_schema(output.get("type", "string")),
                }
                for idx, output in enumerate(entry.get("outputs", []))
            ]
            methods.append(
                {
                    "name": entry.get("name"),
                    "pathname": "",
                    "description": "",
                    "params": params,
                    "returns": returns,
                }
            )
        return {
            "namespace": "default",
            "name": "IdentityRegistry",
            "description": "Identity registry contract interface",
            "version": "1.0",
            "methods": methods,
        }

    def _normalize_identity_ffi(self, ffi: dict, version_suffix: str | None = None) -> dict:
        methods = ffi.get("methods", [])
        for method in methods:
            params = method.get("params", [])
            for idx, param in enumerate(params):
                name = param.get("name", "")
                if name:
                    continue
                if method.get("name") == "orgExists":
                    param["name"] = "orgName"
                else:
                    param["name"] = f"arg{idx}"
            returns = method.get("returns", [])
            for idx, output in enumerate(returns):
                if output.get("name", ""):
                    continue
                output["name"] = f"ret{idx}"
        if version_suffix:
            current = ffi.get("version", "1.0")
            ffi["version"] = f"{current}.{version_suffix}"
        return ffi

    def _write_identity_ffi(self, ffi: dict) -> str:
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        os.makedirs(contract_dir, exist_ok=True)
        ffi_path = os.path.join(contract_dir, "identityFFI.json")
        with open(ffi_path, "w") as handle:
            json.dump(ffi, handle, indent=2)
        return ffi_path

    def _generate_identity_ffi(self, firefly_core_url: str, abi: list) -> dict:
        payload = {
            "name": "IdentityRegistry",
            "namespace": "default",
            "version": "1.0",
            "description": "Identity registry contract interface",
            "input": {"abi": abi},
        }
        response = requests.post(
            f"http://{firefly_core_url}/api/v1/namespaces/default/contracts/interfaces/generate",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60,
        )
        if response.status_code not in [200, 201, 202]:
            raise Exception(
                f"FireFly FFI generate failed with status {response.status_code}: "
                f"{response.text[:500]}"
            )
        return response.json()

    def _register_identity_ffi(self, firefly_core_url: str, abi: list) -> dict:
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        os.makedirs(contract_dir, exist_ok=True)
        existing = self._find_identity_interface_id(firefly_core_url)
        if existing:
            LOG.info(
                "Identity FFI already exists core=%s interface=%s",
                firefly_core_url,
                existing,
            )
            try:
                detail = requests.get(
                    f"http://{firefly_core_url}/api/v1/namespaces/default/contracts/interfaces/{existing}",
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                if detail.status_code in [200, 202]:
                    payload = detail.json()
                    methods = payload.get("methods", [])
                    has_empty = any(
                        (not p.get("name"))
                        for m in methods
                        for p in (m.get("params") or [])
                    )
                    if not has_empty:
                        return {"id": existing, "existing": True}
                else:
                    return {"id": existing, "existing": True}
            except Exception:
                return {"id": existing, "existing": True}
        try:
            LOG.info("Identity FFI generate start core=%s", firefly_core_url)
            ffi = self._generate_identity_ffi(firefly_core_url, abi)
            ffi = self._normalize_identity_ffi(ffi, version_suffix="1")
            self._write_identity_ffi(ffi)
        except Exception as exc:
            fallback_ffi = self._build_identity_ffi(abi)
            fallback_ffi = self._normalize_identity_ffi(fallback_ffi, version_suffix="1")
            with open(os.path.join(contract_dir, "identityFFI.generate_error.log"), "w") as handle:
                handle.write(str(exc))
            self._write_identity_ffi(fallback_ffi)
            ffi = fallback_ffi
            LOG.warning("Identity FFI generate failed core=%s err=%s", firefly_core_url, exc)
        response = requests.post(
            f"http://{firefly_core_url}/api/v1/namespaces/default/contracts/interfaces?confirm=true",
            headers={"Content-Type": "application/json"},
            data=json.dumps(ffi),
            timeout=60,
        )
        LOG.info(
            "Identity FFI register status=%s core=%s body=%s",
            response.status_code,
            firefly_core_url,
            response.text[:300],
        )
        if response.status_code not in [200, 201, 202]:
            try:
                payload = response.json()
            except Exception:
                payload = {}
            if isinstance(payload, dict) and payload.get("error", "").startswith("FF10127"):
                existing = self._find_identity_interface_id(firefly_core_url)
                if existing:
                    return {"id": existing, "existing": True}
            raise Exception(
                f"FireFly FFI registration failed with status {response.status_code}: "
                f"{response.text[:500]}"
            )
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        return payload

    def _find_identity_interface_id(self, firefly_core_url: str) -> str | None:
        response = requests.get(
            f"http://{firefly_core_url}/api/v1/namespaces/default/contracts/interfaces",
            params={"name": "IdentityRegistry"},
            timeout=30,
        )
        if response.status_code != 200:
            return None
        try:
            payload = response.json()
        except Exception:
            return None
        if isinstance(payload, dict):
            payload = payload.get("interfaces") or payload.get("items") or []
        if not isinstance(payload, list) or not payload:
            return None
        return payload[0].get("id")

    def _register_identity_api(
        self,
        firefly_core_url: str,
        interface_id: str,
        contract_address: str,
        api_name: str,
    ) -> dict:
        payload = {
            "name": api_name,
            "interface": {
                "id": interface_id,
            },
            "location": {
                "address": contract_address,
            },
        }
        LOG.info(
            "Identity API register request core=%s name=%s interface=%s address=%s",
            firefly_core_url,
            api_name,
            interface_id,
            contract_address,
        )
        existing_api = None
        existing_api_id = None
        existing_interface_id = None
        existing_location = None
        try:
            api_list = requests.get(
                f"http://{firefly_core_url}/api/v1/namespaces/default/apis",
                params={"name": api_name},
                timeout=30,
            )
            if api_list.status_code == 200:
                api_payload = api_list.json()
                items = api_payload.get("apis") or api_payload.get("items") or []
                if isinstance(items, list) and items:
                    existing_api = items[0]
                    existing_api_id = existing_api.get("id")
                    existing_interface = existing_api.get("interface") or {}
                    existing_interface_id = existing_interface.get("id")
                    existing_location = (existing_api.get("location") or {}).get(
                        "address"
                    )
                    LOG.info(
                        "Identity API existing core=%s name=%s api_id=%s interface=%s address=%s",
                        firefly_core_url,
                        api_name,
                        existing_api_id,
                        existing_interface_id,
                        existing_location,
                    )
                else:
                    LOG.info(
                        "Identity API existing core=%s name=%s none",
                        firefly_core_url,
                        api_name,
                    )
            else:
                LOG.warning(
                    "Identity API list failed core=%s name=%s status=%s body=%s",
                    firefly_core_url,
                    api_name,
                    api_list.status_code,
                    api_list.text[:300],
                )
        except Exception:
            existing_api = None
        last_error = None
        for attempt in range(1, 4):
            if attempt > 1:
                time.sleep(2)
            if existing_api_id:
                try:
                    requests.delete(
                        f"http://{firefly_core_url}/api/v1/namespaces/default/apis/{existing_api_id}",
                        timeout=30,
                    )
                    LOG.info(
                        "Identity API removed before re-create core=%s api_id=%s",
                        firefly_core_url,
                        existing_api_id,
                    )
                    existing_api_id = None
                except Exception:
                    LOG.warning(
                        "Identity API delete failed core=%s api_id=%s",
                        firefly_core_url,
                        existing_api_id,
                    )
            response = requests.post(
                f"http://{firefly_core_url}/api/v1/namespaces/default/apis?confirm=true",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=60,
            )
            LOG.info(
                "Identity API register attempt=%s status=%s core=%s name=%s body=%s",
                attempt,
                response.status_code,
                firefly_core_url,
                api_name,
                response.text[:300],
            )
            if response.status_code in [200, 201, 202]:
                try:
                    payload = response.json()
                except Exception:
                    payload = {}
                if isinstance(payload, list):
                    payload = payload[0] if payload else {}
                return payload
            try:
                payload_body = response.json()
            except Exception:
                payload_body = {}
            if isinstance(payload_body, dict) and payload_body.get("error", "").startswith("FF10127"):
                if existing_api_id and (
                    existing_interface_id != interface_id
                    or (existing_location and existing_location != contract_address)
                ):
                    try:
                        requests.delete(
                            f"http://{firefly_core_url}/api/v1/namespaces/default/apis/{existing_api_id}",
                            timeout=30,
                        )
                    except Exception:
                        return payload_body
                    continue
                return payload_body
            last_error = (
                f"status {response.status_code}: {response.text[:500]}"
            )
        raise Exception(f"FireFly API registration failed after retries: {last_error}")

    def _invoke_identity_api(
        self,
        firefly_core_url: str,
        method: str,
        params: dict,
        mode: str = "invoke",
        api_name: str = "IdentityRegistry",
    ) -> dict:
        payload = {
            "input": params,
        }
        suffix = "?confirm=true" if mode == "invoke" else ""
        url = (
            f"http://{firefly_core_url}/api/v1/namespaces/default/apis/"
            f"{api_name}/{mode}/{method}{suffix}"
        )
        LOG.info(
            "Identity API call url=%s path=/api/v1/namespaces/default/apis/%s/%s/%s",
            url,
            api_name,
            mode,
            method,
        )
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60,
        )
        LOG.info(
            "Identity API response url=%s status=%s",
            url,
            response.status_code,
        )
        if response.status_code not in [200, 201, 202]:
            raise Exception(
                f"FireFly API call failed with status {response.status_code}: "
                f"{response.text[:500]}"
            )
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        return payload

    def _ensure_org_registered(
        self,
        firefly_core_url: str,
        org_name: str,
        org_admin_address: str,
        api_name: str = "IdentityRegistry",
    ) -> None:
        if not org_admin_address:
            raise Exception("org_admin_address is required")
        LOG.info(
            "Identity org register start core=%s name=%s org=%s admin=%s",
            firefly_core_url,
            api_name,
            org_name,
            org_admin_address,
        )
        try:
            self._invoke_identity_api(
                firefly_core_url,
                "createOrganization",
                {
                    "orgName": org_name,
                    "orgAdmin": org_admin_address,
                },
                mode="invoke",
                api_name=api_name,
            )
        except Exception as exc:
            error_text = str(exc)
            if "already exists" in error_text.lower():
                LOG.info(
                    "Identity org register exists core=%s name=%s org=%s",
                    firefly_core_url,
                    api_name,
                    org_name,
                )
                return
            raise
        LOG.info(
            "Identity org register done core=%s name=%s org=%s",
            firefly_core_url,
            api_name,
            org_name,
        )

    def _register_memberships_for_env(self, env: EthEnvironment) -> dict:
        memberships = [rs.membership for rs in env.resource_sets.all() if rs.membership]
        memberships = list({m.id: m for m in memberships}.values())
        if not memberships:
            return {"total": 0, "success": 0, "failed": 0, "results": []}
        results = []
        success = 0
        failed = 0
        system_resource_set = env.resource_sets.filter(
            ethereum_sub_resource_set__org_type=1
        ).first()
        system_firefly = (
            Firefly.objects.filter(resource_set=system_resource_set).first()
            if system_resource_set
            else None
        )
        if not system_firefly:
            return {
                "total": len(memberships),
                "success": 0,
                "failed": len(memberships),
                "results": [
                    {"membership": m.name, "status": "failed", "error": "system firefly not found"}
                    for m in memberships
                ],
            }
        api_name = self._get_identity_api_name(env)
        LOG.info(
            "========== Identity Org Registration START env=%s ==========",
            env.id,
        )
        LOG.info("Identity org registration memberships count=%s", len(memberships))
        LOG.info(
            "Identity org registration memberships env=%s names=%s",
            env.id,
            [m.name for m in memberships],
        )
        system_membership = (
            system_resource_set.membership if system_resource_set else None
        )
        default_admin_address = None
        if system_membership:
            system_identity = (
                EthereumIdentity.objects.filter(
                    eth_environment=env, membership=system_membership
                )
                .order_by("create_at")
                .first()
            )
            if system_identity and system_identity.address:
                default_admin_address = system_identity.address
        if not default_admin_address:
            fallback_identity = (
                EthereumIdentity.objects.filter(eth_environment=env)
                .order_by("create_at")
                .first()
            )
            if fallback_identity and fallback_identity.address:
                default_admin_address = fallback_identity.address
        for membership in memberships:
            try:
                identity = (
                    EthereumIdentity.objects.filter(
                        eth_environment=env, membership=membership
                    )
                    .order_by("create_at")
                    .first()
                )
                org_admin_address = None
                if identity and identity.address:
                    org_admin_address = identity.address
                if not org_admin_address:
                    rs = env.resource_sets.filter(membership=membership).first()
                    firefly = rs.firefly.first() if rs else None
                    if firefly:
                        org_admin_address = self._fetch_firefly_org_admin_address(firefly)
                if not org_admin_address:
                    org_admin_address = default_admin_address
                if not org_admin_address:
                    raise Exception("no org admin address available")
                LOG.info(
                    "Identity org register resolve env=%s membership=%s admin=%s",
                    env.id,
                    membership.name,
                    org_admin_address,
                )
                LOG.info(
                    "Identity org register call env=%s membership=%s core=%s api=%s method=createOrganization",
                    env.id,
                    membership.name,
                    system_firefly.core_url,
                    api_name,
                )
                self._ensure_org_registered(
                    system_firefly.core_url,
                    membership.name,
                    org_admin_address,
                    api_name=api_name,
                )
                results.append({"membership": membership.name, "status": "ok"})
                success += 1
            except Exception as exc:
                LOG.warning(
                    "Identity org register failed env=%s membership=%s error=%s",
                    env.id,
                    membership.name,
                    exc,
                )
                results.append(
                    {"membership": membership.name, "status": "failed", "error": str(exc)}
                )
                failed += 1
        LOG.info(
            "========== Identity Org Registration END env=%s success=%s failed=%s ==========",
            env.id,
            success,
            failed,
        )
        return {
            "total": len(memberships),
            "success": success,
            "failed": failed,
            "results": results,
        }

    def _sync_all_identities_for_env(self, env: EthEnvironment) -> dict:
        identities = EthereumIdentity.objects.filter(eth_environment=env)
        results = []
        success = 0
        failed = 0
        LOG.info("Identity sync-all start env=%s identities=%s", env.id, identities.count())
        firefly_core_url = self._get_firefly_core_url(env)
        api_name = self._get_identity_api_name(env)
        for identity in identities:
            try:
                self._ensure_org_registered(
                    firefly_core_url,
                    identity.membership.name,
                    identity.address,
                    api_name=api_name,
                )
                self._invoke_identity_api(
                    firefly_core_url,
                    "registerIdentity",
                    {
                        "identityAddress": identity.address,
                        "fireflyIdentityId": identity.firefly_identity_id or "",
                        "orgName": identity.membership.name,
                        "customKey": identity.membership.name,
                    },
                    api_name=api_name,
                )
                results.append({"id": str(identity.id), "status": "ok"})
                success += 1
            except Exception as exc:
                results.append(
                    {"id": str(identity.id), "status": "failed", "error": str(exc)}
                )
                failed += 1
        LOG.info(
            "Identity sync-all done env=%s success=%s failed=%s",
            env.id,
            success,
            failed,
        )
        return {
            "total": len(results),
            "success": success,
            "failed": failed,
            "results": results,
        }

    def _load_identity_abi(self):
        contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, "identity-contract")
        abi_path = os.path.join(contract_dir, "IdentityRegistry.abi")
        if not os.path.exists(abi_path):
            return None
        with open(abi_path, "r") as abi_file:
            return json.load(abi_file)

    def _get_firefly_core_url(self, env):
        resource_sets = env.resource_sets.all()
        system_resource_sets = resource_sets.filter(
            ethereum_sub_resource_set__org_type=1
        )
        if not system_resource_sets.exists():
            raise Exception("System resource set not found")
        system_resource_set = system_resource_sets.first()
        firefly = Firefly.objects.filter(resource_set=system_resource_set).first()
        if not firefly:
            raise Exception("Firefly instance not found for system resource set")
        return firefly.core_url

    def _get_identity_api_name(self, env: EthEnvironment) -> str:
        deployment = IdentityDeployment.objects.filter(eth_environment=env).first()
        if deployment and deployment.api_name:
            return deployment.api_name
        return "IdentityRegistry"

    def _deploy_identity_contract(self, env_id):
        env = EthEnvironment.objects.get(id=env_id)
        LOG.info("========== Identity Deploy START env=%s ==========", env.id)
        deployment, _ = IdentityDeployment.objects.get_or_create(
            eth_environment=env
        )
        deployment.status = "SETTINGUP"
        deployment.error = None
        deployment.save(update_fields=["status", "error", "updated_at"])
        env.identity_contract_status = "SETTINGUP"
        env.save(update_fields=["identity_contract_status"])

        abi, bytecode = self._resolve_identity_artifacts()
        firefly_core_url = self._get_firefly_core_url(env)
        LOG.info("Identity contract using FireFly core=%s", firefly_core_url)

        payload = {
            "contract": bytecode,
            "definition": abi,
            "input": [],
        }
        deploy_url = (
            f"http://{firefly_core_url}/api/v1/namespaces/default/"
            "contracts/deploy?confirm=true"
        )
        response = requests.post(
            deploy_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=120,
        )
        LOG.info("Identity contract deploy response status=%s", response.status_code)
        if response.status_code not in [200, 202]:
            raise Exception(
                f"FireFly deployment failed with status {response.status_code}: "
                f"{response.text[:500]}"
            )

        deployment_result = response.json()
        deployment_status = deployment_result.get("status", "Unknown")
        output_data = deployment_result.get("output", {})
        contract_location = output_data.get("contractLocation", {})
        contract_address = contract_location.get("address") or output_data.get("address")
        tx_hash = output_data.get("transactionHash") or deployment_result.get("tx")
        deployment_id = deployment_result.get("id")

        if str(deployment_status).lower() in ["succeeded", "success", "started"]:
            mapped_status = "STARTED"
        elif str(deployment_status).lower() in ["pending", "running"]:
            mapped_status = "SETTINGUP"
        else:
            mapped_status = "FAILED"

        deployment.contract_address = contract_address
        deployment.deployment_tx_hash = tx_hash
        deployment.deployment_id = deployment_id
        deployment.status = mapped_status
        deployment.save(
            update_fields=[
                "contract_address",
                "deployment_tx_hash",
                "deployment_id",
                "status",
                "updated_at",
            ]
        )
        env.identity_contract_status = mapped_status
        env.save(update_fields=["identity_contract_status"])
        LOG.info(
            "Identity contract deploy status=%s address=%s tx=%s",
            mapped_status,
            contract_address,
            tx_hash,
        )

        if mapped_status in ["STARTED", "SETTINGUP"]:
            try:
                # Generate FFI using FireFly (fallback to local builder) and register interfaces/APIs
                api_name = None
                if contract_address:
                    api_name = f"IdentityRegistry-{contract_address[-6:]}"
                else:
                    api_name = f"IdentityRegistry-{int(time.time())}"
                system_rs = env.resource_sets.filter(
                    ethereum_sub_resource_set__org_type=1
                ).first()
                if not system_rs:
                    raise Exception("System resource set not found for identity deploy")
                firefly = Firefly.objects.filter(resource_set=system_rs).first()
                if not firefly:
                    raise Exception("System firefly not found for identity deploy")
                LOG.info(
                    "Identity deploy register start resource_set=%s core=%s",
                    system_rs.id,
                    firefly.core_url,
                )
                ffi_response = self._register_identity_ffi(firefly.core_url, abi)
                interface_id = (
                    ffi_response.get("id")
                    or ffi_response.get("interface", {}).get("id")
                )
                LOG.info(
                    "Identity deploy register interface core=%s interface=%s",
                    firefly.core_url,
                    interface_id,
                )
                if interface_id and contract_address:
                    try:
                        api_response = self._register_identity_api(
                            firefly.core_url,
                            interface_id,
                            contract_address,
                            api_name,
                        )
                    except Exception as exc:
                        error_text = str(exc)
                        if "FF10303" in error_text or "interface" in error_text.lower():
                            LOG.warning(
                                "Identity API register retry: interface missing core=%s interface=%s",
                                firefly.core_url,
                                interface_id,
                            )
                            ffi_response = self._register_identity_ffi(
                                firefly.core_url, abi
                            )
                            interface_id = (
                                ffi_response.get("id")
                                or ffi_response.get("interface", {}).get("id")
                            )
                            api_response = self._register_identity_api(
                                firefly.core_url,
                                interface_id,
                                contract_address,
                                api_name,
                            )
                        else:
                            raise
                    LOG.info(
                        "Identity deploy register api core=%s api_id=%s api_name=%s",
                        firefly.core_url,
                        api_response.get("id"),
                        api_name,
                    )
                    deployment.interface_id = interface_id
                    deployment.api_id = api_response.get("id")
                    deployment.api_name = api_name
                    deployment.api_address = (
                        f"http://{firefly.core_url}/api/v1/namespaces/default/apis/{api_name}"
                    )
                    deployment.save(
                        update_fields=[
                            "interface_id",
                            "api_id",
                            "api_name",
                            "api_address",
                            "updated_at",
                        ]
                    )
                LOG.info("Identity contract FFI/APIs registered for env=%s", env.id)
                org_result = self._register_memberships_for_env(env)
                LOG.info(
                    "Identity contract org registration env=%s success=%s failed=%s",
                    env.id,
                    org_result.get("success"),
                    org_result.get("failed"),
                )
            except Exception as exc:
                deployment.error = f"FFI registration failed: {exc}"
                deployment.save(update_fields=["error", "updated_at"])
                LOG.warning("Identity contract FFI/APIs registration failed: %s", exc)

        LOG.info(
            "========== Identity Deploy END env=%s status=%s ==========",
            env.id,
            mapped_status,
        )
        return {
            "status": mapped_status,
            "contract_address": contract_address,
            "transaction_hash": tx_hash,
            "deployment_id": deployment_id,
        }

    def _redeploy_and_sync(self, env_id):
        LOG.info("Identity contract redeploy+sync start env=%s", env_id)
        deploy_result = self._deploy_identity_contract(env_id)
        env = EthEnvironment.objects.get(id=env_id)
        sync_result = self._sync_all_identities_for_env(env)
        LOG.info(
            "Identity contract redeploy+sync done env=%s deploy_status=%s sync_success=%s sync_failed=%s",
            env_id,
            deploy_result.get("status"),
            sync_result.get("success"),
            sync_result.get("failed"),
        )
        return {"deploy": deploy_result, "sync": sync_result}

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
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="identity-contract/install")
    def install_identity_contract(self, request, pk=None, *args, **kwargs):
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        deployment, _ = IdentityDeployment.objects.get_or_create(
            eth_environment=env
        )
        if deployment.status == "STARTED" and deployment.contract_address:
            LOG.info("Identity contract already deployed env=%s", env.id)
            return Response(
                {
                    "status": deployment.status,
                    "contract_address": deployment.contract_address,
                    "transaction_hash": deployment.deployment_tx_hash,
                    "deployment_id": deployment.deployment_id,
                },
                status=status.HTTP_200_OK,
            )

        env.identity_contract_status = "PENDING"
        env.save(update_fields=["identity_contract_status"])
        deployment.status = "PENDING"
        deployment.error = None
        deployment.save(update_fields=["status", "error", "updated_at"])

        task = Task.objects.create(
            type="IDENTITY_CONTRACT_INSTALL",
            target_type="EthEnvironment",
            target_id=str(env.id),
            status="PENDING",
        )
        LOG.info("Identity contract install task=%s env=%s", task.id, env.id)

        self._start_task(task, self._deploy_identity_contract, env.id)

        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["post"], detail=True, url_path="identity-contract/redeploy")
    def redeploy_identity_contract(self, request, pk=None, *args, **kwargs):
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        env.identity_contract_status = "PENDING"
        env.save(update_fields=["identity_contract_status"])
        deployment, _ = IdentityDeployment.objects.get_or_create(
            eth_environment=env
        )
        deployment.status = "PENDING"
        deployment.error = None
        deployment.save(update_fields=["status", "error", "updated_at"])

        task = Task.objects.create(
            type="IDENTITY_CONTRACT_REDEPLOY",
            target_type="EthEnvironment",
            target_id=str(env.id),
            status="PENDING",
        )
        LOG.info("Identity contract redeploy task=%s env=%s", task.id, env.id)
        self._start_task(task, self._redeploy_and_sync, env.id)
        return Response(
            {"task_id": str(task.id), "status": task.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(methods=["get"], detail=True, url_path="identity-contract")
    def identity_contract_detail(self, request, pk=None, *args, **kwargs):
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        deployment = IdentityDeployment.objects.filter(
            eth_environment=env
        ).first()
        firefly_core_url = None
        try:
            firefly_core_url = self._get_firefly_core_url(env)
        except Exception:
            firefly_core_url = None
        abi = None
        if request.query_params.get("include_abi") in ["1", "true", "yes"]:
            abi = self._load_identity_abi()

        response = {
            "environment_id": str(env.id),
            "status": env.identity_contract_status,
            "deployment": None,
            "abi": abi,
            "firefly_core_url": firefly_core_url,
        }
        if deployment:
            api_name = deployment.api_name or "IdentityRegistry"
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
        启动EthEnvironment - Only changes environment status
        Firefly operations should be called separately from frontend
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

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
        激活EthEnvironment - Only changes environment status
        Firefly operations should be called separately from frontend
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "INITIALIZED":
            return Response(
                {"message": "EthEnvironment has not been initialized"},
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
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "ACTIVATED":
            return Response(
                {"message": "EthEnvironment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers
        org_id = request.data.get("org_id")
        chaincode_id = packageChaincodeForEnv(
            env_id=env.id,
            file_path=FABRIC_CONFIG + "/firefly-go.zip",
            chaincode_name="Firefly",
            version="1.0",
            org_id=org_id,
            auth=headers["Authorization"],
        )

        installChaincodeForEnv(
            env_id=env.id,
            chaincode_id=chaincode_id,
            auth=headers["Authorization"],
        )

        approveChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Firefly",
            auth=headers["Authorization"],
        )

        commmitChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Firefly",
            auth=headers["Authorization"],
        )

        env.firefly_status = "CHAINCODEINSTALLED"
        env.save()
        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="install_oracle")
    def install_oracle(self, request, pk=None, *args, **kwargs):
        """
        安装Oracle
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "ACTIVATED":
            return Response(
                {"message": "EthEnvironment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers
        org_id = request.data.get("org_id")
        chaincode_id = packageChaincodeForEnv(
            env_id=env.id,
            file_path=ORACLE_CONTRACT_PATH + "/oracle-go.zip",
            chaincode_name="Oracle",
            version="1.0",
            org_id=org_id,
            auth=headers["Authorization"],
        )

        installChaincodeForEnv(
            env_id=env.id,
            chaincode_id=chaincode_id,
            auth=headers["Authorization"],
        )

        approveChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Oracle",
            auth=headers["Authorization"],
        )

        commmitChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="Oracle",
            auth=headers["Authorization"],
        )

        env.Oracle_status = "CHAINCODEINSTALLED"
        env.save()

        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="install_dmn_engine")
    def install_dmn_engine(self, request, pk=None, *args, **kwargs):
        """
        启动DMN Engine: 部署合约
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "ACTIVATED":
            return Response(
                {"message": "EthEnvironment has not been activated or has started"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers
        org_id = request.data.get("org_id")

        chaincode_id = packageChaincodeForEnv(
            env_id=env.id,
            file_path=DMN_CONTRACT_PATH + "/dmn-engine.zip",
            chaincode_name="DMNEngine",
            version="1.0",
            org_id=org_id,
            auth=headers["Authorization"],
            language="java",
        )

        installChaincodeForEnv(
            env_id=env.id,
            chaincode_id=chaincode_id,
            auth=headers["Authorization"],
        )

        approveChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="DMNEngine",
            auth=headers["Authorization"],
        )

        commmitChaincodeForEnv(
            env_id=env.id,
            channel_name=DEFAULT_CHANNEL_NAME,
            chaincode_name="DMNEngine",
            auth=headers["Authorization"],
        )

        env.DMN_status = "CHAINCODEINSTALLED"
        env.save()

        return Response(status=status.HTTP_200_OK)

    @action(methods=["get"], detail=False, url_path="requestOracleFFI")
    def requestOracleFFI(self, request, pk=None, *args, **kwargs):
        """
        请求Oracle FFI
        """
        with open(ORACLE_CONTRACT_PATH + "/oracleFFI.json", "r") as f:
            ffiContent = f.read()

        response = {"ffiContent": ffiContent}

        return Response(response, status=status.HTTP_200_OK)
