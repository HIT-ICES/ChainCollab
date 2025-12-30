#
# SPDX-License-Identifier: Apache-2.0
#
from copy import deepcopy
import logging
import json
import traceback

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated

#

from drf_yasg.utils import swagger_auto_schema

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator

from api.config import CELLO_HOME
from api.common.serializers import PageQuerySerializer
from api.utils.common import with_common_response, parse_block_file, to_dict
from api.lib.configtxgen import ConfigTX, ConfigTxGen
from api.lib.peer.channel import Channel as PeerChannel
from api.lib.configtxlator.configtxlator import ConfigTxLator
from api.exceptions import ResourceNotFound, NoResource
from api.models import (
    Channel,
    LoleidoOrganization,
    Node,
    FabricResourceSet,
    Port,
    Network,
    Environment,
    ResourceSet,
)
from api.routes.channel.serializers import (
    ChannelAnchorBody,
    ChannelCreateBody,
    ChannelIDSerializer,
    ChannelListResponse,
    ChannelResponseSerializer,
    ChannelUpdateSerializer,
)

from api.common import ok, err
from api.common.enums import (
    NodeStatus,
    FabricNodeType,
)

LOG = logging.getLogger(__name__)
CONFIGBLOCK_PB = "config_block.pb"
CFG_JSON = "cfg.json"
CFG_PB = "cfg.pb"
DELTA_PB = "delta.pb"
DELTA_JSON = "delta.json"
UPDATED_CFG_JSON = "update_cfg.json"
UPDATED_CFG_PB = "update_cfg.pb"
CFG_DELTA_ENV_JSON = "cfg_delta_env.json"
CFG_DELTA_ENV_PB = "cfg_delta_env.pb"


class ChannelViewSet(viewsets.ViewSet):
    """Class represents Channel related operations."""

    permission_classes = [
        IsAuthenticated,
    ]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        query_serializer=PageQuerySerializer,
        responses=with_common_response({status.HTTP_201_CREATED: ChannelListResponse}),
    )
    def list(self, request, *args, **kwargs):
        """
        List Channels
        :param request: org_id
        :return: channel list
        :rtype: list
        """
        serializer = PageQuerySerializer(data=request.GET)
        if serializer.is_valid(raise_exception=True):
            page = serializer.validated_data.get("page")
            per_page = serializer.validated_data.get("per_page")
            try:
                # org = request.user.organization
                env_id = request.parser_context["kwargs"].get("environment_id")
                env = Environment.objects.get(id=env_id)
                network = env.network
                channels = Channel.objects.filter(network=network)
                channel_list = [
                    {
                        "id": channel.id,
                        "name": channel.name,
                    }
                    for channel in channels
                ]
                return Response(data=ok(channel_list), status=status.HTTP_200_OK)
            except Exception as e:
                return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        request_body=ChannelCreateBody,
        responses=with_common_response({status.HTTP_201_CREATED: ChannelIDSerializer}),
    )
    def create(self, request, pk=None, *args, **kwargs):
        """
        Create Channel
        :param request: create parameter
        :return: Channel ID
        :rtype: uuid
        """

        serializer = ChannelCreateBody(data=request.data)
        if serializer.is_valid(raise_exception=True):
            name = serializer.validated_data.get("name")
            peers = serializer.validated_data.get("peers")
            orderers = serializer.validated_data.get("orderers")
            # env_id = serializer.validated_data.get("env_id")
            env_id = request.parser_context["kwargs"].get("environment_id")

            try:

                # org = request.user.organization
                # TODO 遍历一个环境中的所有节点，不仅仅是一个组织中的 也就是先遍历环境有哪些cello组织（membership），然后再遍历每个组织的所有节点，这些加入一个通道
                # 查询环境 也就需要查询联盟中的   所有membership
                # 1. 需要创建 联盟 环境的数据库，关联到cello的组织  2. 创建通道需要更改逻辑，变为环境中的所有节点 2. 注册cello的组织（咱们的membership）时候，需要创建CA  3. 创建peer order时候需要通过CA创建
                # Check if nodes are running
                # for i in range(len(orderers)):
                #     o = Node.objects.get(id=orderers[i])
                #     if o.status != "running":
                #         raise NoResource
                # for i in range(len(peers)):
                #     p = Node.objects.get(id=peers[i])
                #     if p.status != "running":
                #         raise NoResource
                # NEW LOGIC ---------------------------------------------
                # 1. Divide into groups
                # org_names = []
                # for node in orderers:
                #     org_name = Node.objects.get(id=node).organization.name
                #     if org_name not in [ item["name"] for item in org_names]:
                #         org_names.append({"name": org_name, "peers": [], "orderers": []})
                #     # get the right org
                #     for _org in org_names:
                #         if _org["name"] == org_name:
                #             _org["orderers"].append(node)
                # for node in peers:
                #     org_name = Node.objects.get(id=node).organization.name
                #     if org_name not in [ item["name"] for item in org_names]:
                #         org_names.append({"name": org_name, "peers": [], "orderers": []})
                #     for _org in org_names:
                #         if _org["name"] == org_name:
                #             _org["peers"].append(node)

                # Channel block and tx generate

                # env = Environment.objects.get(id=env_id)
                # env_resource_sets = env.resource_sets.all()
                # fabric_resource_set_name = [rs.sub_resource_set.name for rs in env_resource_sets]
                peer_nodes = Node.objects.filter(id__in=peers)
                fabric_resource_set_name = [
                    node.fabric_resource_set.name for node in peer_nodes
                ]

                network = Environment.objects.get(id=env_id).network
                ConfigTX(network.name).createChannel(name, fabric_resource_set_name)
                ConfigTxGen(network.name).channeltx(
                    profile=name,
                    channelid=name,
                    outputCreateChannelTx="{}.tx".format(name),
                )
                tx_path = "{}/{}/channel-artifacts/{}.tx".format(
                    CELLO_HOME, network.name, name
                )
                block_path = "{}/{}/channel-artifacts/{}.block".format(
                    CELLO_HOME, network.name, name
                )
                # return Response(data=ok({"tx_path": tx_path, "block_path": block_path}), status=status.HTTP_200_OK)
                # access peer to create channel

                # find a orderer to commit -- system orderer
                # ordering_node = Node.objects.filter(organization=org,type='orderer')[0] if len(Node.objects.filter(organization=org,type='orderer')) > 0 else None
                ordering_node = (
                    Node.objects.filter(id__in=orderers)[0]
                    if len(Node.objects.filter(id__in=orderers)) > 0
                    else None
                )
                if not ordering_node:
                    raise NoResource
                # find a peer to access(my org)
                # peer_node = (
                #     Node.objects.filter(organization=org, type="peer")[0]
                #     if len(Node.objects.filter(organization=org, type="peer")) > 0
                #     else None
                # )

                target_peer_node = Node.objects.get(id=peers[0])
                target_peer_fabric_resource_set = target_peer_node.fabric_resource_set

                # Create Channel
                envs = init_env_vars(target_peer_node, target_peer_fabric_resource_set)
                # inject Ordering CA
                orderer_org_name = ordering_node.fabric_resource_set.name
                orderer_org_domain = orderer_org_name.split(".", 1)[1]
                orderer_dir_certificate = (
                    "{}/{}/crypto-config/ordererOrganizations/{}".format(
                        CELLO_HOME, orderer_org_name, orderer_org_domain
                    )
                )
                orderer_dir_certificate = (
                    "{}/{}/crypto-config/ordererOrganizations/{}".format(
                        CELLO_HOME,
                        ordering_node.fabric_resource_set.name,
                        ordering_node.fabric_resource_set.name.split(".", 1)[1],
                    )
                )
                orderer_org_domain = ordering_node.fabric_resource_set.name.split(
                    ".", 1
                )[1]
                envs["ORDERER_CA"] = "{}/msp/tlscacerts/tlsca.{}-cert.pem".format(
                    orderer_dir_certificate, orderer_org_domain
                )
                peer_channel_cli = PeerChannel("v2.2.0", **envs)

                port = Port.objects.get(node=ordering_node, internal=7050)
                peer_channel_cli.create(
                    channel=name,
                    # orderer_url="{}.{}:{}".format(
                    #     ordering_node.name,
                    #     ordering_node.urls.split(".", 2)[2],
                    #     str(port.external),
                    # ),
                    orderer_url="{}:{}".format(
                        ordering_node.urls,
                        str(port.external),
                    ),
                    channel_tx=tx_path,
                    output_block=block_path,
                )
                print("JOIN ALL PEER")
                # Join Channel New Logic ---------------------------------
                # gether all peer node
                nodes = Node.objects.filter(
                    id__in=peers,
                    type="peer",
                )

                for node in nodes:
                    envs = init_env_vars(node, node.fabric_resource_set)
                    # inject Ordering CA
                    join_peers(envs, block_path)

                # DB handler

                channel = Channel(name=name, network=network)
                channel.save()
                fabric_resource_sets_to_add = [
                    node.fabric_resource_set for node in peer_nodes
                ]
                for frs in fabric_resource_sets_to_add:
                    channel.fabric_resource_set.add(frs)
                orderers_to_add = [Node.objects.get(id=node) for node in orderers]
                for orderer in orderers_to_add:
                    channel.orderers.add(orderer)
                response = ChannelIDSerializer(data=channel.__dict__)
                if response.is_valid(raise_exception=True):
                    return Response(
                        ok(response.validated_data), status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                traceback.print_exc()
                return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses=with_common_response({status.HTTP_200_OK: ChannelResponseSerializer}),
    )
    def retrieve(self, request, pk=None):
        """
        Retrieve channel
        :param request: retrieve parameter
        :param pk: primary key
        :return: none
        :rtype: rest_framework.status
        """
        try:
            channel = Channel.objects.get(id=pk)
            response = ChannelResponseSerializer(instance=channel)
            return Response(ok(response.data), status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            raise ResourceNotFound

    @swagger_auto_schema(
        request_body=ChannelUpdateSerializer,
        responses=with_common_response({status.HTTP_202_ACCEPTED: "Accepted"}),
    )
    def update(self, request, pk=None):
        """
        Update channel
        :param request: update parameters
        :param pk: primary key
        :return: none
        :rtype: rest_framework.status
        """
        serializer = ChannelUpdateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            channel = Channel.objects.get(id=pk)
            org = request.user.organization
            try:
                # Read uploaded file in cache without saving it on disk.
                file = request.FILES.get("data").read()
                json_data = file.decode("utf8").replace("'", '"')
                data = json.loads(json_data)
                msp_id = serializer.validated_data.get("msp_id")
                org_type = serializer.validated_data.get("org_type")
                # Validate uploaded config file
                try:
                    config = data["config"]["channel_group"]["groups"][org_type][
                        "groups"
                    ][msp_id]
                except KeyError:
                    LOG.error("config file not found")
                    raise ResourceNotFound

                try:
                    # Read current channel config from local disk
                    with open(
                        channel.get_channel_artifacts_path(CFG_JSON),
                        "r",
                        encoding="utf-8",
                    ) as f:
                        LOG.info("load current config success")
                        current_config = json.load(f)
                except FileNotFoundError:
                    LOG.error("current config file not found")
                    raise ResourceNotFound

                # Create a new org
                new_org = FabricResourceSet.objects.create(
                    name=org.name,
                )
                LOG.info("new org created")
                updated_config = deepcopy(current_config)
                updated_config["channel_group"]["groups"]["Application"]["groups"][
                    msp_id
                ] = config
                LOG.info("update config success", updated_config)

                # Update and save the config with new org
                with open(
                    channel.get_channel_artifacts_path(UPDATED_CFG_JSON),
                    "w",
                    encoding="utf-8",
                ) as f:
                    LOG.info("save updated config success")
                    json.dump(updated_config, f, sort_keys=False)

                # Encode it into pb.
                ConfigTxLator().proto_encode(
                    input=channel.get_channel_artifacts_path(UPDATED_CFG_JSON),
                    type="common.Config",
                    output=channel.get_channel_artifacts_path(UPDATED_CFG_PB),
                )
                LOG.info("encode config to pb success")

                # Calculate the config delta between pb files
                ConfigTxLator().compute_update(
                    original=channel.get_channel_artifacts_path(CFG_PB),
                    updated=channel.get_channel_artifacts_path(UPDATED_CFG_PB),
                    channel_id=channel.name,
                    output=channel.get_channel_artifacts_path(DELTA_PB),
                )
                LOG.info("compute config delta success")
                # Decode the config delta pb into json
                config_update = ConfigTxLator().proto_decode(
                    input=channel.get_channel_artifacts_path(DELTA_PB),
                    type="common.ConfigUpdate",
                )
                LOG.info("decode config delta to json success")
                # Wrap the config update as envelope
                updated_config = {
                    "payload": {
                        "header": {
                            "channel_header": {
                                "channel_id": channel.name,
                                "type": 2,
                            }
                        },
                        "data": {"config_update": to_dict(config_update)},
                    }
                }
                with open(
                    channel.get_channel_artifacts_path(CFG_JSON), "w", encoding="utf-8"
                ) as f:
                    LOG.info("save config to json success")
                    json.dump(updated_config, f, sort_keys=False)

                # Encode the config update envelope into pb
                ConfigTxLator().proto_encode(
                    input=channel.get_channel_artifacts_path(CFG_JSON),
                    type="common.Envelope",
                    output=channel.get_channel_artifacts_path(CFG_DELTA_ENV_PB),
                )
                LOG.info("Encode the config update envelope success")

                # Peers to send the update transaction
                nodes = Node.objects.filter(
                    organization=org,
                    type=FabricNodeType.Peer.name.lower(),
                    status=NodeStatus.Running.name.lower(),
                )

                for node in nodes:
                    dir_node = "{}/{}/crypto-config/peerOrganizations".format(
                        CELLO_HOME, org.name
                    )
                    env = {
                        "FABRIC_CFG_PATH": "{}/{}/peers/{}/".format(
                            dir_node, org.name, node.name + "." + org.name
                        ),
                    }
                    cli = PeerChannel("v2.2.0", **env)
                    cli.signconfigtx(
                        channel.get_channel_artifacts_path(CFG_DELTA_ENV_PB)
                    )
                    LOG.info("Peers to send the update transaction success")

                # Save a new organization to db.
                new_org.save()
                LOG.info("new_org save success")
                return Response(ok(None), status=status.HTTP_202_ACCEPTED)
            except ObjectDoesNotExist:
                raise ResourceNotFound

    @swagger_auto_schema(
        responses=with_common_response({status.HTTP_200_OK: "Accepted"}),
    )
    @action(methods=["get"], detail=True, url_path="configs")
    def get_channel_org_config(self, request, pk=None):
        try:
            org = request.user.organization
            channel = Channel.objects.get(id=pk)
            path = channel.get_channel_config_path()
            node = Node.objects.filter(
                organization=org,
                type=FabricNodeType.Peer.name.lower(),
                status=NodeStatus.Running.name.lower(),
            ).first()
            dir_node = "{}/{}/crypto-config/peerOrganizations".format(
                CELLO_HOME, org.name
            )
            # env = {
            #     "FABRIC_CFG_PATH": "{}/{}/peers/{}/".format(
            #         dir_node, org.name, node.name + "." + org.name
            #     ),
            # }
            envs = init_env_vars(node, node.fabric_resource_set)
            peer_channel_cli = PeerChannel("v2.2.0", **envs)
            peer_channel_cli.fetch(option="config", channel=channel.name, path=path)

            # Decode latest config block into json
            config = ConfigTxLator().proto_decode(input=path, type="common.Block")
            config = parse_block_file(config)

            # Prepare return data
            data = {
                "config": config,
                "organization": org.name,
                # TODO: create a method on Organization or Node to return msp_id
                "msp_id": "{}".format(org.name.split(".")[0].capitalize()),
            }

            # Save as a json file for future usage
            with open(
                channel.get_channel_artifacts_path(CFG_DELTA_ENV_JSON),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(config, f, sort_keys=False)
            # Encode block file as pb
            ConfigTxLator().proto_encode(
                input=channel.get_channel_artifacts_path(CFG_DELTA_ENV_JSON),
                type="common.Config",
                output=channel.get_channel_artifacts_path(CFG_PB),
            )
            return Response(data=data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            raise ResourceNotFound

    @swagger_auto_schema(
        responses=with_common_response({status.HTTP_200_OK: "Accepted"}),
    )
    @action(methods=["post"], detail=True, url_path="anchors")
    def set_org_channel_anchor(self, request, pk=None, *args, **kwargs):
        serializer = ChannelAnchorBody(data=request.data)
        if serializer.is_valid(raise_exception=True):
            # org = request.user.organization
            orderers = serializer.validated_data.get("orderers")
            channel = Channel.objects.get(id=pk)
            anchor_peers = serializer.validated_data.get("anchor_peers")
            resource_set_id = serializer.validated_data.get("resource_set_id")
            resource_set = ResourceSet.objects.get(id=resource_set_id)
            fabric_resource_set = resource_set.sub_resource_set
            path = channel.get_channel_artifacts_path(CONFIGBLOCK_PB)
            anchor_peer_nodes = Node.objects.filter(
                fabric_resource_set=fabric_resource_set,
                id__in=anchor_peers,
                type=FabricNodeType.Peer.name.lower(),
                status=NodeStatus.Running.name.lower(),
            )
            # TODO: 权限检查
            peer_node = anchor_peer_nodes.first()
            # init envs
            envs = init_env_vars(peer_node, peer_node.fabric_resource_set)
            # find orderer node to construct env
            ordering_node = (
                Node.objects.filter(id__in=orderers)[0]
                if len(Node.objects.filter(id__in=orderers)) > 0
                else None
            )
            if not ordering_node:
                raise NoResource

            # inject Ordering CA
            orderer_org_name = ordering_node.fabric_resource_set.name
            orderer_org_domain = orderer_org_name.split(".", 1)[1]
            orderer_dir_certificate = (
                "{}/{}/crypto-config/ordererOrganizations/{}".format(
                    CELLO_HOME,
                    ordering_node.fabric_resource_set.name,
                    ordering_node.fabric_resource_set.name.split(".", 1)[1],
                )
            )
            orderer_org_domain = ordering_node.fabric_resource_set.name.split(".", 1)[1]
            envs["ORDERER_CA"] = "{}/msp/tlscacerts/tlsca.{}-cert.pem".format(
                orderer_dir_certificate, orderer_org_domain
            )
            # fetch channel config
            peer_channel_cli = PeerChannel("v2.2.0", **envs)
            peer_channel_cli.fetch(option="config", channel=channel.name, path=path)

            # Decode latest config block into json
            config = ConfigTxLator().proto_decode(input=path, type="common.Block")
            config = parse_block_file(config)

            # Save as a json file for future usage
            # equals to config.json
            with open(
                channel.get_channel_artifacts_path(CFG_JSON), "w", encoding="utf-8"
            ) as f:
                json.dump(config, f, sort_keys=False)

            try:
                # Read current channel config from local disk
                with open(
                    channel.get_channel_artifacts_path(CFG_JSON),
                    "r",
                    encoding="utf-8",
                ) as f:
                    LOG.info("load current config success")
                    current_config = json.load(f)
            except FileNotFoundError:
                LOG.error("current config file not found")
                raise ResourceNotFound

            org_name_id = "{}".format(
                fabric_resource_set.name.split(".")[0].capitalize()
            )
            # Validate config file
            try:
                anchor_config = current_config["channel_group"]["groups"][
                    "Application"
                ]["groups"][org_name_id]["values"]
            except KeyError:
                LOG.error("config file key not found")
                raise ResourceNotFound

            if "AnchorPeers" in anchor_config:
                LOG.error("anchor peers have been set")
                raise ResourceNotFound
            # build anchor peer hosts
            anchor_peers_hosts = []
            for peer_node in anchor_peer_nodes:
                anchor_peers_hosts.append(
                    {
                        "host": peer_node.name
                        + "."
                        + peer_node.fabric_resource_set.name,
                        "port": 7051,
                    }
                )
            # build anchor updated config
            updated_config = deepcopy(current_config)
            updated_config["channel_group"]["groups"]["Application"]["groups"][
                org_name_id
            ]["values"]["AnchorPeers"] = {
                "mod_policy": "Admins",
                "value": {"anchor_peers": anchor_peers_hosts},
                "version": "0",
            }

            LOG.info("update config success", updated_config)

            # Update and save the config with anchor config
            with open(
                channel.get_channel_artifacts_path(UPDATED_CFG_JSON),
                "w",
                encoding="utf-8",
            ) as f:
                LOG.info("save updated config success")
                json.dump(updated_config, f, sort_keys=False)

            # # Encode config json into pb.
            # Encode block file as pb
            ConfigTxLator().proto_encode(
                input=channel.get_channel_artifacts_path(CFG_JSON),
                type="common.Config",
                output=channel.get_channel_artifacts_path(CFG_PB),
            )
            LOG.info("encode cfg_json config to pb success")
            # Encode updated_config json into pb.
            ConfigTxLator().proto_encode(
                input=channel.get_channel_artifacts_path(UPDATED_CFG_JSON),
                type="common.Config",
                output=channel.get_channel_artifacts_path(UPDATED_CFG_PB),
            )
            LOG.info("encode updated_cfg_json config to pb success")

            # Calculate the config delta between pb files
            ConfigTxLator().compute_update(
                original=channel.get_channel_artifacts_path(CFG_PB),
                updated=channel.get_channel_artifacts_path(UPDATED_CFG_PB),
                channel_id=channel.name,
                output=channel.get_channel_artifacts_path(DELTA_PB),
            )
            LOG.info("compute config delta success")
            # Decode the config delta pb into json
            config_update = ConfigTxLator().proto_decode(
                input=channel.get_channel_artifacts_path(DELTA_PB),
                type="common.ConfigUpdate",
            )
            LOG.info("decode config delta to json success")
            # Wrap the config update as envelope
            updated_config = {
                "payload": {
                    "header": {
                        "channel_header": {
                            "channel_id": channel.name,
                            "type": 2,
                        }
                    },
                    "data": {"config_update": to_dict(config_update)},
                }
            }
            with open(
                channel.get_channel_artifacts_path(CFG_DELTA_ENV_JSON),
                "w",
                encoding="utf-8",
            ) as f:
                LOG.info("save config to json success")
                json.dump(updated_config, f, sort_keys=False)

            # Encode the config update envelope into pb
            ConfigTxLator().proto_encode(
                input=channel.get_channel_artifacts_path(CFG_DELTA_ENV_JSON),
                type="common.Envelope",
                output=channel.get_channel_artifacts_path(CFG_DELTA_ENV_PB),
            )
            LOG.info("Encode the config update envelope success")

            # Peers to send the update transaction
            # Because we are updating a section of the channel configuration that only affects Org1, other channel members do not need to approve the channel update.
            port = Port.objects.get(node=ordering_node, internal=7050)
            peer_channel_cli.update(
                channel_tx=channel.get_channel_artifacts_path(CFG_DELTA_ENV_PB),
                channel_id=channel.name,
                # orderer_host_port="{}.{}:{}".format(
                #     ordering_node.name,
                #     ordering_node.urls.split(".", 2)[2],
                #     str(port.external),
                # ),
                orderer_host_port="{}:{}".format(
                    ordering_node.urls,
                    str(port.external),
                ),
            )
            LOG.info("Peers to send the update transaction success")

            # Prepare return data
            data = {
                "config": config,
                "organization": fabric_resource_set.name,
                # TODO: create a method on Organization or Node to return msp_id
                "msp_id": "{}".format(
                    fabric_resource_set.name.split(".")[0].capitalize()
                ),
            }
            return Response(data=data, status=status.HTTP_200_OK)


def init_env_vars(node, org):
    """
    Initialize environment variables for peer channel CLI.
    :param node: Node object
    :param org: Organization object.
    :return env: dict
    """
    org_name = org.name
    org_domain = org_name.split(".", 1)[1]
    dir_certificate = "{}/{}/crypto-config/ordererOrganizations/{}".format(
        CELLO_HOME, org_name, org_domain
    )
    dir_node = "{}/{}/crypto-config/peerOrganizations".format(CELLO_HOME, org_name)
    port = Port.objects.get(node=node, internal=7051)
    envs = {
        "CORE_PEER_TLS_ENABLED": "true",
        # "Org1.cello.comMSP"
        "CORE_PEER_LOCALMSPID": "{}MSP".format(org_name.capitalize()),
        "CORE_PEER_TLS_ROOTCERT_FILE": "{}/{}/peers/{}/tls/ca.crt".format(
            dir_node, org_name, node.name + "." + org_name
        ),
        # "CORE_PEER_ADDRESS": "{}:{}".format(
        #     node.name + "." + org_name, str(7051)),
        "CORE_PEER_ADDRESS": "{}:{}".format(
            node.name + "." + org_name, str(port.external)
        ),
        "CORE_PEER_MSPCONFIGPATH": "{}/{}/users/Admin@{}/msp".format(
            dir_node, org_name, org_name
        ),
        "FABRIC_CFG_PATH": "{}/{}/peers/{}/".format(
            dir_node, org_name, node.name + "." + org_name
        ),
        "ORDERER_CA": "{}/msp/tlscacerts/tlsca.{}-cert.pem".format(
            dir_certificate, org_domain
        ),
    }
    print(envs)
    return envs


def join_peers(envs, block_path):
    """
    Join peer nodes to the channel.
    :param envs: environments variables for peer CLI.
    :param block_path: Path to file containing genesis block
    """
    # Join the peers to the channel.
    peer_channel_cli = PeerChannel("v2.2.0", **envs)
    peer_channel_cli.join(block_file=block_path)
