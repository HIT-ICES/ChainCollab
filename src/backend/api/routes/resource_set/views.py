import json
import os
import traceback

from requests import post
from rest_framework import viewsets, status
from rest_framework.response import Response
from api.common import ok, err
from api.config import CURRENT_IP
from api.utils.test_time import timeitwithname

from .serializers import ResourceSetSerializer
from rest_framework.decorators import action

from api.utils.port_picker import set_ports_mapping, find_available_ports
from django.db import transaction

from api.models import (
    Consortium,
    Environment,
    EthNode,
    Port,
    ResourceSet,
    Agent,
    Membership,
    FabricResourceSet,
    LoleidoOrganization,
)


class ResourceSetViewSet(viewsets.ViewSet):
    """
    ResourceSet管理
    """

    def list(self, request, *args, **kwargs):
        """
        获取ResourceSet列表
        """
        environment_id = request.parser_context["kwargs"].get("environment_id")
        queryset = ResourceSet.objects.filter(
            environment_id=environment_id
        )
        org_id = request.query_params.get("org_id",None)
        membership_id = request.query_params.get("membership_id", None)

        params = []

        if membership_id is not None:
            params.append(membership_id)
        elif org_id is not None:
            try:
                org = LoleidoOrganization.objects.get(pk=org_id)
            except LoleidoOrganization.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            memberships = Membership.objects.filter(loleido_organization=org)
            params = [membership.id for membership in memberships]
        else:
            serializer = ResourceSetSerializer(queryset, many=True)
            return Response(serializer.data)
        
        queryset = queryset.filter(membership_id__in=params)
        serializer = ResourceSetSerializer(queryset, many=True)
        return Response(serializer.data)
            




    def create(self, request, *args, **kwargs):
        """
        创建ResourceSet
        """
        environment_id = request.parser_context["kwargs"].get("environment_id")
        membership_id = request.data.get("membership_id")
        agent_id = request.data.get("agent_id")
        name = request.data.get("name")
        try:
            environment = Environment.objects.get(pk=environment_id)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            membership = Membership.objects.get(pk=membership_id)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        resource_set = ResourceSet.objects.create(
            environment=environment,
            membership=membership,
            name=name,
            agent=agent,
        )

        sub_resource_set = FabricResourceSet.objects.create(
            resource_set=resource_set,
            org_type=0,  # 0: user, 1: system
            name=resource_set.name,
        )

        serializer = ResourceSetSerializer(resource_set)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取ResourceSet详情
        """
        try:
            resource_set = ResourceSet.objects.get(pk=pk)
        except ResourceSet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ResourceSetSerializer(resource_set)
        return Response(serializer.data)

    def destroy(self, request, pk=None, *args, **kwargs):
        """
        删除ResourceSet
        """
        try:
            resource_set = ResourceSet.objects.get(pk=pk)
        except ResourceSet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        resource_set.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # def update(self, request, pk=None):
    #     """
    #     更新ResourceSet
    #     """
    #     try:
    #         resource_set = ResourceSet.objects.get(pk=pk)
    #     except ResourceSet.DoesNotExist:
    #         return Response(status=status.HTTP_404_NOT_FOUND)
    #     serializer = ResourceSetSerializer(resource_set, data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EthereumResourceSetViewSet(viewsets.ViewSet):
    def _set_port(self, node, agent):
        """
        get free port from agent,

        :param node: node obj
        :param agent: agent obj
        :return: none
        :rtype: none
        """
        ip = agent.urls.split(":")[1].strip("//")
        ports = find_available_ports(ip, node.id, agent.id, 1)
        set_ports_mapping(node.id, [{"internal": 7054, "external": ports[0]}], True)
        
    # def _create_start_eth_node(self, ca_name, port_map, org_name, type, infos=None):
    #     try:
    #         self._node_create_agent(ca_name)
    #     except Exception as e:
    #         raise Exception(e)
    
    
    def _node_create_agent(self, name, port_map):
        try:
            data = {
                "node_name": name,
                "port_map": port_map,
            }
            response = post(f"""http://{CURRENT_IP}:7001/api/v1/ethnode""", data=data)
            if response.status_code == 200:
                txt = json.loads(response.text)
                return txt["res"]
            else:
                txt = json.loads(response.text)
                print(txt)
                raise Exception(txt["res"])
        except Exception as e:
            raise Exception(e)
        
    def _create_folders_up_to_path( current_path, path):
    # 使用os.path.normpath来确保路径格式的一致性

        normalized_path = os.path.normpath(path)

        # 获取目标路径的各个部分
        folders = normalized_path.split(os.sep)

        # 逐个创建文件夹
        for folder in folders:
            current_path = os.path.join(current_path, folder)
            if not os.path.exists(current_path):
                os.makedirs(current_path)
                print(f"Created folder: {current_path}")
    
    @transaction.atomic
    @action(methods=["post"], detail=False, url_path="node_create")
    def node_create(self, request, pk=None, *args, **kwargs):
        print("begin eth node crate post api")
        try:
            resource_set_id = request.parser_context["kwargs"].get("resource_set_id")
            resource_set = ResourceSet.objects.get(pk=resource_set_id)
            ethereum_resource_set = resource_set.sub_resource_set.get()
            agent = resource_set.agent
            org_name = ethereum_resource_set.name
            node_name = request.data.get("name", None)
            
            node = EthNode(
                name=node_name,
                # JsonField
                # urls="ca." + org_name,
                agent=agent,
                # type="ca",
            )
            node.save()
            
            # 可能需要修改
            self._set_port(node, agent)
            
            port_map = {
                a["internal"]: a["external"]
                for a in Port.objects.filter(node=node)
                .values("internal", "external")
                .all()
            }.__repr__()
            
            # self._create_start_eth_node(
            #     ca_name=org_name,
            #     port_map=port_map,
            #     org_name=org_name,
            #     type="ca",
            #     infos=request.data,
            # )
            self._node_create_agent(
                name=node_name,
                port_map=port_map,
            )
            
            return Response(
                data=ok("ca create success"), status=status.HTTP_202_ACCEPTED
            )
            
            
        except Exception as e:
            print("________ERRORR_________")
            traceback.print_exc(e)
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)    
    
    @action(methods=["post"], detail=True, url_path="join")
    @timeitwithname("JoinEthereum")
    def join(self, request, pk=None, *args, **kwargs):
        membership_id = request.data.get("membership_id", None)
        try:
            membership = Membership.objects.get(pk=membership_id)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        
        # try:
        #     environment = EthEnvironment.objects.get(pk=pk)
        # except EthEnvironment.DoesNotExist:
        #     return Response(status=status.HTTP_404_NOT_FOUND)

        # if environment.status != "INITIALIZED":
        #     return Response(
        #         {"message": "Ethereum Environment has not been initialized or has started"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        return Response(status=status.HTTP_201_CREATED)
            
    