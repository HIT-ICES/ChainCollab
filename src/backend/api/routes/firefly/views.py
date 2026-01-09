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
from subprocess import Popen

from api.config import CELLO_HOME, CURRENT_IP, DEFAULT_CHANNEL_NAME

from api.utils.port_picker import set_ports_mapping, find_available_ports
from requests import get, post
import json
import traceback
from api.models import (
    EthEnvironment,
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
                org_name = peer_resource_set.sub_resource_set.name
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
        """
        Initialize Firefly for Ethereum environment
        1. Get system node URL from EthNode
        2. Generate single connector config
        3. Initialize Firefly stack with ff CLI
        4. Configure docker network
        """
        try:
            LOG.info("Starting Ethereum Firefly initialization")
            env_id = request.parser_context["kwargs"].get("environment_id")
            env = EthEnvironment.objects.get(id=env_id)

            # Get all resource sets for this environment
            resource_sets = env.resource_sets.all()

            # Find the system node to get its URL
            system_resource_sets = resource_sets.filter(
                ethereum_sub_resource_sets__org_type=1
            )
            if not system_resource_sets.exists():
                raise Exception("System resource set not found")

            system_resource_set = system_resource_sets.first()

            # Import EthNode and EthNodeType at function level to avoid circular imports
            from api.models import EthNode
            from api.common.enums import EthNodeType

            system_nodes = EthNode.objects.filter(
                fabric_resource_set__resource_set=system_resource_set,
                type=EthNodeType.System.value
            )

            if not system_nodes.exists():
                raise Exception("System node not found")

            system_node = system_nodes.first()
            system_node_url = f"http://{system_node.name}:8545"

            LOG.info(f"Using system node URL: {system_node_url}")

            # Calculate total node count: system nodes + organization nodes
            system_node_count = system_nodes.count()

            # Get organization resource sets (org_type != 1 means organization type)
            org_resource_sets = resource_sets.exclude(
                ethereum_sub_resource_sets__org_type=1
            )

            # Count organization nodes
            org_node_count = EthNode.objects.filter(
                fabric_resource_set__resource_set__in=org_resource_sets,
                type=EthNodeType.Organization.value
            ).count()

            total_member_count = system_node_count + org_node_count

            LOG.info(f"Total member count: {total_member_count} (system: {system_node_count}, organization: {org_node_count})")

            # Generate single connector config for the environment
            connector_config_dir = os.path.join(CELLO_HOME, env.name.lower())
            os.makedirs(connector_config_dir, exist_ok=True)

            # Generate evmconnect.yml
            connector_config = {
                "connectors": [
                    {
                        "type": "ethereum",
                        "server": {
                            "port": 5102
                        },
                        "ethereum": {
                            "url": system_node_url
                        }
                    }
                ]
            }

            connector_config_path = os.path.join(connector_config_dir, "evmconnect.yml")
            with open(connector_config_path, "w") as f:
                yaml.dump(connector_config, f, default_flow_style=False)

            LOG.info(f"Generated connector config at {connector_config_path}")

            # Initialize Firefly stack using Firefly_cli
            firefly_name = "cello_" + env.name.lower()
            ff_cli = Firefly_cli()

            # Call the init_eth method from Firefly_cli
            network_name = ff_cli.init_eth(
                firefly_name=firefly_name,
                system_node_url=system_node_url,
                system_node_name=system_node.name,
                connector_config_path=connector_config_path,
                member_count=total_member_count
            )

            LOG.info(f"Firefly initialization completed for {firefly_name}")

            # Save Firefly objects to database
            firefly_stack_path = os.path.expanduser("~/.firefly/stacks/") + firefly_name

            # Read stack.json to get member/organization names and ports
            with open(os.path.join(firefly_stack_path, "stack.json"), "r") as file:
                stack_data = json.load(file)
                # For Ethereum stacks, use orgName from members array
                account_names = [member["orgName"] for member in stack_data["members"]]

            LOG.info(f"Found {len(account_names)} accounts: {account_names}")

            # Create Firefly objects for each resource set
            for index, resource_set in enumerate(resource_sets):
                # Get member info from stack.json
                member = stack_data["members"][index]

                # Get core port from stack.json or docker-compose ports
                # For Ethereum, core port is in exposedFireflyPort
                core_port = member["exposedFireflyPort"]

                # Get sandbox port from stack.json
                sandbox_port = member["exposedSandboxPort"]

                # Get evmconnect port from stack.json
                evmconnect_port = member["exposedConnectorPort"]

                LOG.info(f"Creating Firefly object for {account_names[index]}: core={core_port}, sandbox={sandbox_port}, evmconnect={evmconnect_port}")

                # Create and save Firefly object
                firefly = Firefly(
                    resource_set=resource_set,
                    org_name=account_names[index],
                    core_url=f"{CURRENT_IP}:{core_port}",
                    sandbox_url=f"{CURRENT_IP}:{sandbox_port}",
                    fab_connect_url=f"{CURRENT_IP}:{evmconnect_port}",
                )
                firefly.save()
                LOG.info(f"Saved Firefly object for {account_names[index]}")

            return Response(
                {
                    "message": "Firefly Ethereum initialization successful",
                    "firefly_name": firefly_name,
                    "system_node_url": system_node_url,
                    "connector_config": connector_config_path,
                    "network": network_name,
                    "firefly_count": len(account_names)
                },
                status=status.HTTP_202_ACCEPTED
            )

        except EthEnvironment.DoesNotExist:
            LOG.error(f"Environment {env_id} not found")
            return Response(
                err("Environment not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            LOG.exception(f"Firefly init_eth failed: {e}")
            traceback.print_exc()
            return Response(
                err(f"Firefly init fail: {str(e)}"),
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(methods=["post"], detail=False, url_path="start_eth")
    def start_eth(self, request, pk=None, *args, **kwargs):
        """
        Start Firefly for Ethereum environment
        Transfer 10 ether from sender account to each of the 3 organization accounts
        """
        try:
            env_id = request.parser_context["kwargs"].get("environment_id")
            env = EthEnvironment.objects.get(id=env_id)
            firefly_name = "cello_" + env.name.lower()

            # Get all resource sets for this environment
            resource_sets = env.resource_sets.all()

            # Find the system node
            system_resource_sets = resource_sets.filter(
                ethereum_sub_resource_sets__org_type=1
            )
            if not system_resource_sets.exists():
                raise Exception("System resource set not found")

            system_resource_set = system_resource_sets.first()

            # Import EthNode and EthNodeType at function level to avoid circular imports
            from api.models import EthNode
            from api.common.enums import EthNodeType

            system_nodes = EthNode.objects.filter(
                fabric_resource_set__resource_set=system_resource_set,
                type=EthNodeType.System.value
            )

            if not system_nodes.exists():
                raise Exception("System node not found")

            system_node = system_nodes.first()
            container_name = system_node.name  # Use system node container name

            LOG.info(f"Using system node container: {container_name}")

            # Read organization accounts from stackState.json
            firefly_stack_path = os.path.expanduser("~/.firefly/stacks/") + firefly_name
            stack_state_file = os.path.join(firefly_stack_path, "init/stackState.json")

            with open(stack_state_file, "r") as file:
                stack_data = json.load(file)
                # Get the 3 account addresses
                accounts = [account["address"] for account in stack_data["accounts"][:3]]

            LOG.info(f"Found {len(accounts)} accounts to fund: {accounts}")

            # Sender account (predefined)
            sender_account = "0x365acf78c44060caf3a4789d804df11e3b4aa17d"

            # Enter the eth container and transfer funds
            geth_attach_command = ["docker", "exec", "-i", container_name, "geth", "attach"]
            geth_attach_process = subprocess.Popen(
                geth_attach_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Transfer 10 ether to each account
            for account in accounts:
                transfer_command = f"eth.sendTransaction({{from: \"{sender_account}\", to: \"{account}\", value: web3.toWei(10, 'ether')}})\n"
                geth_attach_process.stdin.write(transfer_command)
                geth_attach_process.stdin.flush()
                LOG.info(f"Transferred 10 ether from {sender_account} to {account}")

            # Close geth attach process
            geth_attach_process.stdin.write("exit\n")
            geth_attach_process.stdin.flush()
            geth_attach_process.communicate()

            # Start Firefly
            Firefly_cli().start(firefly_name=firefly_name)

            return Response(
                {
                    "message": "Firefly Ethereum started successfully",
                    "firefly_name": firefly_name,
                    "funded_accounts": accounts,
                    "amount_per_account": "10 ether"
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            LOG.exception(f"Firefly start_eth failed: {e}")
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)