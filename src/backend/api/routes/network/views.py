#
# SPDX-License-Identifier: Apache-2.0
#
import logging
import base64
import shutil
import os

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from api.exceptions import ResourceNotFound, ResourceExists
from api.routes.network.serializers import (
    NetworkQuery,
    NetworkListResponse,
    NetworkMemberResponse,
    NetworkCreateBody,
    NetworkIDSerializer,
)
from api.utils.common import with_common_response
from api.lib.configtxgen import ConfigTX, ConfigTxGen
from api.models import Network, Node, Port, ResourceSet, Environment
from api.config import CELLO_HOME
from api.utils import zip_file
from api.lib.agent import AgentHandler
from api.common import ok, err
import threading

LOG = logging.getLogger(__name__)


class NetworkViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, ]

    def _genesis2base64(self, network):
        """
        convert genesis.block to Base64
        :param network: network id
        :return: genesis block
        :rtype: bytearray
        """
        try:
            dir_node = "{}/{}/".format(CELLO_HOME, network)
            name = "genesis.block"
            zname = "block.zip"
            zip_file("{}{}".format(dir_node, name),
                     "{}{}".format(dir_node, zname))
            with open("{}{}".format(dir_node, zname), "rb") as f_block:
                block = base64.b64encode(f_block.read())
            return block
        except Exception as e:
            raise e

    @swagger_auto_schema(
        query_serializer=NetworkQuery,
        responses=with_common_response(
            with_common_response({status.HTTP_200_OK: NetworkListResponse})
        ),
    )
    def list(self, request):
        """
        List network
        :param request: query parameter
        :return: network list
        :rtype: list
        """
        try:
            serializer = NetworkQuery(data=request.GET)
            if serializer.is_valid(raise_exception=True):
                page = serializer.validated_data.get("page", 1)
                per_page = serializer.validated_data.get("page", 10)
                org = request.user.organization
                networks = org.network
                if not networks:
                    return Response(ok(data={"total": 0, "data": None}), status=status.HTTP_200_OK)
                p = Paginator([networks], per_page)
                networks = p.page(page)
                networks = [
                    {
                        "id": network.id,
                        "name": network.name,
                        "created_at": network.created_at,
                    }
                    for network in networks
                ]
                response = NetworkListResponse(
                    data={"total": p.count, "data": networks}
                )
                if response.is_valid(raise_exception=True):
                    return Response(
                        ok(response.validated_data), status=status.HTTP_200_OK
                    )
            return Response(ok(data={"total": 0, "data": None}), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                err(e.args), status=status.HTTP_400_BAD_REQUEST
            )

    def _agent_params(self, pk, network_id):
        """
        get node's params from db
        :param node: node id
        :return: info
        """
        try:
            network = Network.objects.get(id=network_id)
            # print(network.genesisblock)
            node = Node.objects.get(id=pk)
            org = node.fabric_resource_set
            if org is None:
                raise ResourceNotFound(detail="Organization Not Found")
            # network2 = org.network
            # network = network2
            if network is None:
                raise ResourceNotFound(detail="Network Not Found")
            agent = org.resource_set.agent
            if agent is None:
                raise ResourceNotFound(detail="Agent Not Found")
            ports = Port.objects.filter(node=node)
            if ports is None:
                raise ResourceNotFound(detail="Port Not Found")

            info = {}

            org_name = org.name if node.type == "peer" else org.name.split(".", 1)[
                1]
            # get info of node, e.g, tls, msp, config.
            info["status"] = node.status
            info["msp"] = node.msp
            info["tls"] = node.tls
            info["config_file"] = node.config_file
            info["type"] = node.type
            info["name"] = "{}.{}".format(node.name, org_name)
            info["bootstrap_block"] = network.genesisblock
            info["urls"] = agent.urls
            info["network_type"] = network.type
            info["agent_type"] = agent.type
            info["ports"] = ports
            return info
        except Exception as e:
            raise e

    def _start_node(self, pk,network_id):
        """
        start node from agent
        :param node: node id
        :return: null
        """
        try:
            node_qs = Node.objects.filter(id=pk)
            infos = self._agent_params(pk,network_id)
            agent = AgentHandler(infos)
            cid = agent.create(infos)
            if cid:
                node_qs.update(cid=cid, status="running")
            else:
                raise ResourceNotFound(detail="Container Not Built")
        except Exception as e:
            print(e)
            raise e

    @swagger_auto_schema(
        request_body=NetworkCreateBody,
        responses=with_common_response(
            {status.HTTP_201_CREATED: NetworkIDSerializer}
        ),
    )
    def create(self, request, pk=None, *args, **kwargs):
        """
        Create Network, Adding All org in the environment(consortium)
        :param request: create parameter
        :return: organization ID
        :rtype: uuid
        """
        try:
            serializer = NetworkCreateBody(data=request.data)
            if serializer.is_valid(raise_exception=True):
                name = serializer.validated_data.get("name")
                consensus = serializer.validated_data.get("consensus")
                # database = serializer.validated_data.get("database")
                env_id = request.parser_context.get("kwargs").get("environment_id")
                # lo_org = request.user.organization
                env = Environment.objects.get(pk=env_id)
                if env is None:
                    raise ResourceNotFound(detail="Environment Not Found")
                if env.network:
                    raise ResourceExists(
                        detail="Network exists for the environment")

                resource_sets = list(ResourceSet.objects.filter(environment=env).all())
                org_names = [resource_set.sub_resource_set.name for resource_set in resource_sets]
                nodes = Node.objects.filter(fabric_resource_set__name__in=org_names).exclude(type="ca")

                orderers = []
                peers = []
                # for org_name in org_names:
                #     orderers.append({"name": org_name, "hosts": []})
                #     peers.append({"name": org_name, "hosts": []})

                for node in nodes:
                    node_type = node.type
                    if (node_type=="peer"):
                        if(node.fabric_resource_set.name not in [peer["name"] for peer in peers]):
                            peers.append({"name": node.fabric_resource_set.name, "hosts": []})
                        org_peer = next((p for p in peers if p["name"] == node.fabric_resource_set.name), None)
                        if org_peer:
                            org_peer["hosts"].append({"name":node.name})
                    if (node_type=="orderer"):
                        if(node.fabric_resource_set.name not in [orderer["name"] for orderer in orderers]):
                            orderers.append({"name": node.fabric_resource_set.name, "hosts": []})
                        org_orderer = next((o for o in orderers if o["name"] == node.fabric_resource_set.name), None)
                        if org_orderer:
                            org_orderer["hosts"].append({"name":node.name})

                ConfigTX(name).create(consensus=consensus,
                                      orderers=orderers, peers=peers)
                ConfigTxGen(name).genesis()

                block = self._genesis2base64(name)

                network = Network(
                    name=name, consensus=consensus, genesisblock=block)
                network.save()
                env.network = network
                env.save()

                for resource_set in resource_sets:
                    fabric_resource_set = resource_set.sub_resource_set
                    fabric_resource_set.network = network
                    fabric_resource_set.save()

                # new start nodes  ----------------------
                # find all node in the environment

                threads = []
                for node in nodes:
                    try:
                        thread=threading.Thread(target=self._start_node,
                                         args=(node.id,network.id))
                        thread.start()
                        threads.append(thread)
                    except Exception as e:
                        raise e
                for thread in threads:
                    thread.join()
                # new logic  ----------------------
                response = NetworkIDSerializer(data=network.__dict__)
                if response.is_valid(raise_exception=True):
                    return Response(
                        ok(response.validated_data), status=status.HTTP_201_CREATED
                    )
        except ResourceExists as e:
            raise e
        except Exception as e:
            print(e)
            return Response(
                err(e.args), status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(responses=with_common_response())
    def retrieve(self, request, pk=None):
        """
        Get Network
        Get network information
        """
        pass

    @swagger_auto_schema(
        responses=with_common_response(
            {status.HTTP_202_ACCEPTED: "No Content"}
        )
    )
    def destroy(self, request, pk=None):
        """
        Delete Network
        :param request: destory parameter
        :param pk: primary key
        :return: none
        :rtype: rest_framework.status
        """
        try:
            network = Network.objects.get(pk=pk)
            path = "{}/{}".format(CELLO_HOME, network.name)
            if os.path.exists(path):
                shutil.rmtree(path, True)
            network.delete()
            return Response(ok(None), status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response(
                err(e.args), status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        methods=["get"],
        responses=with_common_response(
            {status.HTTP_200_OK: NetworkMemberResponse}
        ),
    )
    @swagger_auto_schema(
        methods=["post"],
        responses=with_common_response(
            {status.HTTP_200_OK: NetworkMemberResponse}
        ),
    )
    @action(methods=["get", "post"], detail=True, url_path="peers")
    def peers(self, request, pk=None):
        """
        get:
        Get Peers
        Get peers of network.
        post:
        Add New Peer
        Add peer into network
        """
        pass

    @swagger_auto_schema(
        methods=["delete"],
        responses=with_common_response(
            {status.HTTP_200_OK: NetworkMemberResponse}
        ),
    )
    @action(methods=["delete"], detail=True, url_path="peers/<str:peer_id>")
    def delete_peer(self, request, pk=None, peer_id=None):
        """
        delete:
        Delete Peer
        Delete peer in network
        """
        pass
