import logging
import os
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
import yaml
import json
import subprocess
from subprocess import Popen, call

from api.config import CELLO_HOME, CURRENT_IP, DEFAULT_CHANNEL_NAME, FABRIC_CONFIG

from api.utils.port_picker import set_ports_mapping, find_available_ports
from requests import get, post
import json
import traceback
from api.models import (
    Node,
    Port,
    FabricCAServerType,
    Environment,
    ResourceSet,
    Firefly,
    LoleidoOrganization,
    Membership,
    FabricResourceSet,
)
from api.common import ok, err

from api.lib.firefly.firefly import Firefly_cli

LOG = logging.getLogger(__name__)


class FireflyViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticated,
    ]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request, *args, **kwargs):
        try:
            org_id = request.query_params.get("org_id", None)
            env_id = request.parser_context["kwargs"].get("environment_id")
            membership_id = request.query_params.get("membership_id", None)
            env = Environment.objects.get(id=env_id)
            if org_id:
                organization = LoleidoOrganization.objects.get(id=org_id)
                memberships = Membership.objects.filter(
                    loleido_organization=organization
                )
                resource_sets = ResourceSet.objects.filter(
                    environment=env, membership__in=memberships
                )
            elif membership_id:
                membership = Membership.objects.get(id=membership_id)
                resource_sets = ResourceSet.objects.filter(
                    environment=env, membership=membership
                )
            else:
                resource_sets = ResourceSet.objects.filter(environment=env)

            fireflys = Firefly.objects.filter(resource_set__in=resource_sets)
            data = []
            for firefly in fireflys:
                data.append(
                    {
                        "id": firefly.id,
                        "org_name": firefly.org_name,
                        "core_url": firefly.core_url,
                        "sandbox_url": firefly.sandbox_url,
                        "membership_id": firefly.resource_set.membership.id,
                        "membership_name": firefly.resource_set.membership.name,
                    }
                )
            return Response(ok(data))
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            firefly_id = request.parser_context["kwargs"].get("pk")
            firefly = Firefly.objects.get(id=firefly_id)
            data = {
                "id": firefly.id,
                "org_name": firefly.org_name,
                "core_url": firefly.core_url,
                "sandbox_url": firefly.sandbox_url,
                "membership_id": firefly.resource_set.membership.id,
                "membership_name": firefly.resource_set.membership.name,
            }
            return Response(ok(data))
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False, url_path="init")
    def init(self, request, pk=None, *args, **kwargs):
        try:
            # env_id = request.data["env_id"]
            env_id = request.parser_context["kwargs"].get("environment_id")
            # channel_name = request.data["channel_name"]
            channel_name = DEFAULT_CHANNEL_NAME
            # firefly_chaincode_name = request.data["firefly_chaincode_name"]
            firefly_chaincode_name = "Firefly"
            env = Environment.objects.get(id=env_id)
            # find orgs by env
            # peer_resource_sets = env.resource_sets.all().filter(
            #     sub_resource_set__org_type=0
            # )
            peer_resource_sets = env.resource_sets.all()
            ccp_file_paths = []
            for peer_resource_set in peer_resource_sets:
                org_name = peer_resource_set.sub_resource_set.get().name
                ccp_file_paths.append(
                    "{}/{}/crypto-config/peerOrganizations/{}/{}_ccp.yaml".format(
                        CELLO_HOME, org_name, org_name, org_name
                    )
                )
            firefly_name = "cello_" + env.name.lower()
            Firefly_cli().init(
                firefly_name=firefly_name,
                channel_name=channel_name,
                firefly_chaincode_name=firefly_chaincode_name,
                ccp_files_path=ccp_file_paths,
            )
            # save db
            firefly_stack_path = os.path.expanduser("~/.firefly/stacks/") + firefly_name
            # 读取YAML文件
            with open(firefly_stack_path + "/docker-compose.yml", "r") as file:
                data = yaml.safe_load(file)
            with open(firefly_stack_path + "/init/stackState.json") as file:
                stact_data = json.load(file)
                account_names = [account["name"] for account in stact_data["accounts"]]

            for index, peer_resource_set in enumerate(peer_resource_sets):
                core_port = data["services"]["sandbox_" + str(index)]["environment"][
                    "FF_ENDPOINT"
                ]
                core_port = core_port.split(":")[2]
                sandbox_port = data["services"]["sandbox_" + str(index)]["ports"]
                sandbox_port = int(sandbox_port[0].split(":")[0])
                fab_connect_port = int(
                    data["services"]["fabconnect_" + str(index)]["ports"][0].split(":")[
                        0
                    ]
                )
                firefly = Firefly(
                    resource_set=peer_resource_set,
                    org_name=account_names[index],
                    core_url=f"{CURRENT_IP}:{core_port}",
                    sandbox_url=f"{CURRENT_IP}:{sandbox_port}",
                    fab_connect_url=f"{CURRENT_IP}:{fab_connect_port}",
                )
                firefly.save()
            return Response(status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=False, url_path="start")
    def start(self, request, pk=None, *args, **kwargs):
        try:
            env_id = request.parser_context["kwargs"].get("environment_id")
            env = Environment.objects.get(id=env_id)
            Firefly_cli().start(firefly_name="cello_" + env.name.lower())
            return Response(status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=True, url_path="remove")
    def remove(self, request, pk=None):
        try:
            env_id = request.data["env_id"]
            env = Environment.objects.get(id=env_id)
            Firefly_cli().remove(firefly_name="cello_" + env.name)
            # TODO 清除数据库
            # find orgs by env
            middle_orgs = ResourceSet.objects.filter(
                cello_organization__org_type=0, environment=env
            )
            fireflys = Firefly.objects.filter(middle_organization__in=middle_orgs)
            for firefly in fireflys:
                print(firefly.id)
                firefly.delete()
            return Response(status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["get"], detail=False, url_path="get_firefly_with_msp")
    def get_firefly_with_msp(self, request, *args, **kwargs):
        msp = request.query_params.get("msp", None)
        if msp is None:
            return Response(err("msp is required"), status=status.HTTP_400_BAD_REQUEST)
        fabric_resouce_set = FabricResourceSet.objects.get(msp=msp)
        resource_set = ResourceSet.objects.get(sub_resource_set=fabric_resouce_set)
        firefly = Firefly.objects.get(resource_set=resource_set)
        data = {
            "id": firefly.id,
            "org_name": firefly.org_name,
            "core_url": firefly.core_url,
            "sandbox_url": firefly.sandbox_url,
            "membership_id": firefly.resource_set.membership.id,
            "membership_name": firefly.resource_set.membership.name,
        }
        return Response(ok(data))
    
    @action(methods=["post"], detail=False, url_path="init_eth")
    def init_eth(self, request, pk=None, *args, **kwargs):
        try:
            datadir_command = f"""geth --datadir ./datadir account new"""
            datadir_output = call(datadir_command, shell=True)
            compose_file_path = "/home/rhq/workspace/projects/ICES/ChainCollab/src/backend/opt/config/ethereum/docker-compose.yml"
            subprocess.run(["docker-compose", "-f", compose_file_path, "up", "-d"], check=True)
            container_id = subprocess.check_output(["docker", "ps", "-q", "-f", "name=mybootnode"]).decode().strip()
            container_name = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}", "-f", "name=mybootnode"]).decode().strip()
            
            geth_attach_command = ["docker", "exec", "-i", container_id, "geth", "attach"]
            geth_attach_process = subprocess.Popen(geth_attach_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            geth_attach_process.stdin.write("personal.unlockAccount(\"0x365acf78c44060caf3a4789d804df11e3b4aa17d\", \"\", 0)\n")
            geth_attach_process.stdin.flush()
            output, error = geth_attach_process.communicate()
            print("Geth Attach Output:", output)
            print("Geth Attach Error:", error)
            
            firefly_name = "eth-rpc1"  # 替换为实际的 firefly 名称
            manifest_file_path = "/home/qkl03/workspace/ICES/files/manifest.json"  # 替换为实际的 manifest 文件路径
            remote_node_url = f"http://{container_name}:8545"
            ff_init_command = [
                self.ff_path,
                "init",
                "ethereum",
                firefly_name,
                "-n",
                "remote-rpc",
                "--remote-node-url",
                remote_node_url,
                "--chain-id",
                "3456",
                "--connector-config",
                "/home/qkl03/workspace/ICES/files/ethereum_connector_config.json",
                "-m",
                manifest_file_path,
                "--remote-node-deploy",
            ]
            output = call(ff_init_command, shell=True)
            
            # 获取容器的网络信息
            inspect_command = ["docker", "inspect", container_name]
            inspect_output = subprocess.check_output(inspect_command).decode().strip()
            container_info = json.loads(inspect_output)[0]
            network_name = list(container_info["NetworkSettings"]["Networks"].keys())[0]
            # firefly_config_path需要替换
            firefly_stack_path = self.firefly_config_path + firefly_name
            # 读取YAML文件
            with open(firefly_stack_path + "/docker-compose.override.yml", "r") as file:
                data = yaml.safe_load(file)
            # 添加配置
            data["networks"] = {"default": {"name": network_name, "external": True}}
            # 将修改后的数据写回文件
            with open(firefly_stack_path + "/docker-compose.override.yml", "w") as file:
                yaml.dump(data, file)
        except Exception as e:
            traceback.print_exc(e)
            err_msg = "firefly init fail for {}!".format(e)
            raise Exception(err_msg)

    @action(methods=["post"], detail=False, url_path="start_eth")
    def start_eth(self, request, pk=None, *args, **kwargs):
        # 需要在启动前，进入对应的eth容器，并记录那3个组织账号，给组织转账
        try:
            
            # env_id = request.parser_context["kwargs"].get("environment_id")
            # env = Environment.objects.get(id=env_id)
            # Firefly_cli().start(firefly_name="cello_" + env.name.lower())
            # return Response(status=status.HTTP_202_ACCEPTED)
            
            env_id = request.parser_context["kwargs"].get("environment_id")
            env = Environment.objects.get(id=env_id)
            firefly_name = "cello_" + env.name.lower()

            # 进入对应的第一个eth容器
            container_name = "mybootnode"  
            geth_attach_command = ["docker", "exec", "-i", container_name, "geth", "attach"]
            geth_attach_process = subprocess.Popen(geth_attach_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            get_accounts_command = "eth.accounts\n"
            geth_attach_process.stdin.write(get_accounts_command)
            geth_attach_process.stdin.flush()
            output, error = geth_attach_process.communicate()
            accounts = output.strip().split('\n')[-1].strip('[]').replace("'", "").split(', ')[:3]

            sender_account = "0x365acf78c44060caf3a4789d804df11e3b4aa17d"  # 发送者账号由初始规定，可根据实际情况修改
            unlock_command = f"personal.unlockAccount(\"{sender_account}\", \"\", 0)\n"
            geth_attach_process.stdin.write(unlock_command)
            geth_attach_process.stdin.flush()
            for account in accounts:
                transfer_command = f"eth.sendTransaction({{from: \"{sender_account}\", to: \"{account}\", value: web3.toWei(1, 'ether')}})\n"
                geth_attach_process.stdin.write(transfer_command)
                geth_attach_process.stdin.flush()

            # 启动Firefly，存疑
            Firefly_cli().start(firefly_name=firefly_name)
            return Response(status=status.HTTP_202_ACCEPTED)
        
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)