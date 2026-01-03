import logging
from requests import post
from rest_framework import viewsets, status
from rest_framework.response import Response

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
)
from api.config import (
    DEFAULT_AGENT,
    DEFAULT_CHANNEL_NAME,
    FABRIC_CONFIG,
    CURRENT_IP,
    ORACLE_CONTRACT_PATH,
    DMN_CONTRACT_PATH,
)
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

        node_name = "orderer1"
        orderer_domain_name = (
            node_name + "0." + fabric_resource_set.name.split(".", 1)[1]
        )

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
        node_name = "peer1"
        peer_domain_name = node_name + "0." + fabric_resource_set.name
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

        node_name = "peer1"
        peer_domain_name = node_name + "0." + fabric_resource_set.name
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

    @action(methods=["post"], detail=True, url_path="init")
    @timeitwithname("InitEth")
    def init(self, request, pk=None, *args, **kwargs):
        """
        初始化EthEnvironment
        """
        
        try:
            env = Environment.objects.get(pk=pk)
        except Environment.DoesNotExist:
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
            name=membership.name, environment=env, membership=membership, agent=agent
        )
        
        ethereum_resource_set = EthereumResourceSet.objects.create(
            resource_set=resource_set,
            org_type=1,
            name=membership.name + ".org" + ".com",
            # msp=membership.name + ".org" + ".com" + "OrdererMSP",
        )
        
        # # firefly 相关操作
        
        # headers = request.headers
        # post(
        #     f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/fireflys/init_eth",
        #     headers={"Authorization": headers["Authorization"]},
        # )
        
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
                environment = Environment.objects.get(pk=pk)
            except Environment.DoesNotExist:
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
                environment=environment,
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
                ethereum_sub_resource_sets__org_type=1
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
        启动EthEnvironment
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        headers = request.headers
        post(
            f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/fireflys/start_eth",
            headers={"Authorization": headers["Authorization"]},
        )
        
        env = EthEnvironment.objects.get(pk=pk)
        env.status = "STARTED"
        env.save()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="activate")
    @timeitwithname("ActivateEth")
    def activate(self, request, pk=None, *args, **kwargs):
        """
        激活EthEnvironment
        """
        try:
            env = EthEnvironment.objects.get(pk=pk)
        except EthEnvironment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if env.status != "STARTED":
            return Response(
                {"message": "EthEnvironment has not been started or has activated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = request.headers

        # Activate environment logic here

        env.status = "ACTIVATED"
        env.save()

        return Response(status=status.HTTP_201_CREATED)

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
