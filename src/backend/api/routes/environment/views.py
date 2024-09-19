from requests import post
from rest_framework import viewsets, status
from rest_framework.response import Response

from api.common.enums import FabricNodeType

from .serializers import EnvironmentSerializer
from rest_framework.decorators import action

from api.models import (
    Consortium,
    Environment,
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

        # 创建节点
        post(
            f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{resource_set.id}/nodes",
            data={"num": 1, "type": "peer", "name": node_name},
            headers={"Authorization": headers["Authorization"]},
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
                    node.id
                    for node in orderer_resource_set.sub_resource_set.get().node.all()
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
                    node.id
                    for node in peer_resource_set.sub_resource_set.get().node.all()
                    if node.type != "ca"
                ]
                for peer_resource_set in peer_resource_sets
            ]
        )

        # append orderer resource peers
        peer_ids.append(
            flatten(
                [
                    [
                        node.id
                        for node in orderer_resource_set.sub_resource_set.get().node.all()
                        if node.type != "ca" and node.type != "orderer"
                    ]
                    for orderer_resource_set in orderer_resource_sets
                ]
            )
        )
        channel_name = DEFAULT_CHANNEL_NAME
        response = post(
            f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/channels",
            data={
                "orderers": orderer_ids,
                "peers": peer_ids,
                "name": channel_name,
                "environment_id": env.id,
            },
            headers={"Authorization": headers["Authorization"]},
        )

        # print(response.json())
        def _generateAnchorPeers(peer_resource_set):
            post(
                f"http://{CURRENT_IP}:8000/api/v1/environments/{env.id}/channels/{response.json()['data']['id']}/anchors",
                data={
                    "anchor_peers": [
                        [
                            node.id
                            for node in peer_resource_set.sub_resource_set.get().node.all()
                            if node.type != "ca" and node.type != "orderer"
                        ][0]
                        # peer_resource_set.sub_resource_set.get().node.all()[0].id
                    ],
                    "orderers": orderer_ids,
                    "resource_set_id": peer_resource_set.id,
                },
                headers={"Authorization": headers["Authorization"]},
            )
            post(
                f"http://{CURRENT_IP}:8000/api/v1/resource_sets/{peer_resource_set.id}/cas/ccp/generate",
                data={
                    "channel_name": channel_name,
                    "peer_id": [
                        node.id
                        for node in peer_resource_set.sub_resource_set.get().node.all()
                        if node.type != "ca" and node.type != "orderer"
                    ][0],
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
