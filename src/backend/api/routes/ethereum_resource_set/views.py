import json
import os
import traceback

from requests import post
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db import transaction

from api.common import ok, err
from api.config import CURRENT_IP
from api.utils.test_time import timeitwithname
from api.utils.port_picker import set_ports_mapping, find_available_ports
from api.models import (
    EthNode,
    Port,
    ResourceSet,
    Membership,
)


class EthereumResourceSetViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _set_port(self, node, agent):
        """
        get free port from agent,

        :param node: node obj
        :param agent: agent obj
        :return: none
        :rtype: none
        """
        ip = agent.urls.split(":")[1].strip("//")
        # Ethereum nodes need 2 ports: 8545 (HTTP RPC) and 30303 (P2P)
        ports = find_available_ports(ip, node.id, agent.id, 2)
        set_ports_mapping(
            node.id,
            [
                {"internal": 8545, "external": ports[0]},
                {"internal": 30303, "external": ports[1]},
            ],
            new=True,
        )

    def _node_create_agent(self, name, port_map, type=None, sys_enode=None):
        try:
            payload = {
                "name": name,
                "port_map": json.dumps(port_map),
            }

            # Add type if provided
            if type:
                payload["type"] = type

            # Add sys_enode if provided
            if sys_enode:
                payload["sys_enode"] = sys_enode

            response = post(
                f"http://{CURRENT_IP}:7001/api/v1/ethnode",
                data=payload,
            )
            if 200 <= response.status_code < 300:
                txt = json.loads(response.text)
                return txt.get("res", {})
            txt = json.loads(response.text)
            print(txt)
            raise Exception(txt.get("res", txt))
        except Exception as e:
            raise Exception(e)

    def _create_folders_up_to_path(current_path, path):
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
            ethereum_resource_set = resource_set.ethereum_sub_resource_set
            agent = resource_set.agent
            org_name = ethereum_resource_set.name
            node_name = request.data.get("name", None)
            type = request.data.get("type", None)
            sys_enode_input = request.data.get("sys_enode", None)

            # Create EthNode and save all information
            node = EthNode(
                name=node_name,
                agent=agent,
                fabric_resource_set=ethereum_resource_set,
                type=type,  # Store type in the model
            )

            # For organization nodes, store the input bootnode enode
            if sys_enode_input:
                node.sys_enode = sys_enode_input

            node.save()

            # 可能需要修改
            self._set_port(node, agent)

            port_map = {
                str(a["internal"]): int(a["external"])
                for a in Port.objects.filter(eth_node=node)
                .values("internal", "external")
                .all()
            }

            # Prepare data for agent - send type and sys_enode for provisioning
            agent_data = {
                "name": node_name,
                "port_map": port_map,
            }

            if type:
                agent_data["type"] = type
            if sys_enode_input:
                agent_data["sys_enode"] = sys_enode_input

            result = self._node_create_agent(**agent_data)

            # Log the result for debugging
            print(f"Agent result: {result}")
            print(f"Node type: {type}")

            # If this is a system node, update sys_enode with the actual enode from the container
            if type == "system":
                print("This is a system node, checking for enode in result...")
                if result:
                    print(
                        f"Result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}"
                    )
                    # Check in result['data']['enode']
                    if isinstance(result, dict) and "data" in result and isinstance(
                        result["data"], dict
                    ):
                        if "enode" in result["data"]:
                            enode = result["data"]["enode"]
                            print(f"Found enode in data: {enode}")
                            node.sys_enode = enode
                            node.save()
                            print(f"Saved enode to node {node.id}")
                        else:
                            print("WARNING: enode not found in result['data']!")
                    else:
                        print("WARNING: result structure is not as expected!")
                else:
                    print("WARNING: result is None or empty!")

            return Response(
                data=ok({"message": "node created successfully", "result": result}),
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            print("________ERRORR_________")
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=True, url_path="join")
    @timeitwithname("JoinEthereum")
    def join(self, request, pk=None, *args, **kwargs):
        membership_id = request.data.get("membership_id", None)
        try:
            membership = Membership.objects.get(pk=membership_id)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_201_CREATED)
