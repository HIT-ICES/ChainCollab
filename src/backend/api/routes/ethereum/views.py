#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import os
import traceback
import logging

logger = logging.getLogger(__name__)

from drf_yasg.utils import swagger_auto_schema
from api.config import ETHEREUM_CONTRACT_STORE
from api.models import (
    EthereumContract,
    EthereumDeployment,
    Environment,
    LoleidoOrganization,
)
from api.utils.common import make_uuid
from api.common.serializers import PageQuerySerializer
from api.utils.common import with_common_response
from api.exceptions import ResourceNotFound

from api.routes.ethereum.serializers import (
    EthereumContractIDSerializer,
    EthereumContractCompileBody,
    EthereumContractUploadBody,
    EthereumContractDeployBody,
    EthereumContractResponseSerializer,
    EthereumContractListResponse,
    EthereumContractCompileResponse,
    EthereumContractUploadResponse,
    EthereumContractDeployResponse,
)

from api.common import ok, err
from api.lib.ethereum.solc_compiler import SolidityCompiler
import requests
import json
from api.models import Firefly, EthEnvironment

class EthereumContractViewSet(viewsets.ViewSet):
    """Class represents Ethereum Contract related operations."""

    permission_classes = [
        IsAuthenticated,
    ]

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific Ethereum contract by ID.

        :param request: HTTP request
        :return: Contract details
        """
        try:
            contract_id = request.parser_context["kwargs"].get("pk")
            contract = EthereumContract.objects.get(id=contract_id)
            contract_data = {
                "id": contract.id,
                "name": contract.name,
                "version": contract.version,
                "filename": contract.filename,
                "creator": contract.creator.name,
                "language": contract.language,
                "create_ts": contract.create_ts,
                "contract_address": contract.contract_address,
                "deployment_tx_hash": contract.deployment_tx_hash,
                "contract_content": contract.contract_content,
            }
            return Response(data=contract_data, status=status.HTTP_200_OK)
        except EthereumContract.DoesNotExist:
            return Response(
                err("Contract not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        query_serializer=PageQuerySerializer,
        responses=with_common_response(
            {status.HTTP_200_OK: EthereumContractListResponse}
        ),
    )
    def list(self, request, *args, **kwargs):
        """
        List Ethereum Contracts in an environment.

        :param request: org_id
        :return: contract list
        :rtype: list
        """
        try:
            env_id = request.parser_context["kwargs"].get("environment_id")
            contracts = EthereumContract.objects.filter(environment_id=env_id)

            contracts_list = [
                {
                    "id": contract.id,
                    "name": contract.name,
                    "version": contract.version,
                    "creator": contract.creator.name,
                    "language": contract.language,
                    "create_ts": contract.create_ts,
                    "contract_address": contract.contract_address,
                }
                for contract in contracts
            ]
            return Response(data=contracts_list, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=EthereumContractCompileBody,
        responses=with_common_response(
            {status.HTTP_200_OK: EthereumContractCompileResponse}
        ),
    )
    @action(detail=False, methods=["post"])
    def compile(self, request, *args, **kwargs):
        """
        Compile a Solidity smart contract using solc.

        This endpoint compiles an already uploaded contract.
        It requires a contract_id parameter to identify the contract to compile.

        :param request: Contains org_id and contract_id (required)
        :return: Compiled contract details with ABI and bytecode
        """
        serializer = EthereumContractCompileBody(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            return Response(err(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get("name")
        contract_id = request.data.get("contract_id")  # Required: contract must be uploaded first

        if not contract_id:
            logger.error("contract_id is required for compilation")
            return Response(
                err("contract_id is required. Please upload the contract first."),
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"Compiling existing contract: {contract_id}")

        try:
            # Get existing contract
            try:
                contract = EthereumContract.objects.get(id=contract_id)
                logger.info(f"Found existing contract: {contract.name}")
            except EthereumContract.DoesNotExist:
                logger.error(f"Contract {contract_id} not found in database")
                return Response(
                    err(f"Contract {contract_id} not found. Please upload it first."),
                    status=status.HTTP_404_NOT_FOUND
                )

            # Use already uploaded contract file
            file_path = os.path.join(ETHEREUM_CONTRACT_STORE, contract_id)
            sol_file_path = os.path.join(file_path, contract.filename)

            if not os.path.exists(sol_file_path):
                logger.error(f"Contract file not found: {sol_file_path}")
                return Response(
                    err("Contract file not found. Please upload it first."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Compile the contract using solc
            compiler = SolidityCompiler()

            # Check if solc is installed
            is_installed, version_or_error = compiler.check_installation()
            if not is_installed:
                return Response(
                    err(f"Solidity compiler not available: {version_or_error}"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(f"=== Starting compilation for contract: {name} ===")
            logger.info(f"Contract file: {sol_file_path}")

            # Compile the contract
            output_json_path = os.path.join(file_path, f"{name}.json")
            return_code, compiled_data, error_msg = compiler.compile_contract(
                sol_file_path, output_json_path
            )

            if return_code != 0:
                logger.error(f"✗ Compilation failed with return code: {return_code}")
                logger.error(f"Error: {error_msg}")
            else:
                logger.info(f"✓ Compilation completed successfully (return code: {return_code})")

            if return_code != 0:
                return Response(
                    err(f"Compilation failed: {error_msg}"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Extract contract information using convert_contract
            from api.lib.ethereum.convert_contract import extract_contract_info
            try:
                contract_info = extract_contract_info(compiled_data)
                logger.info(f"✓ Extracted contract info successfully")
                logger.info(f"  - Bytecode length: {len(contract_info.get('contract', ''))} bytes")
                logger.info(f"  - ABI entries: {len(contract_info.get('definition', []))} functions/events")
            except Exception as e:
                logger.error(f"✗ Failed to extract contract info: {e}")
                available_keys = list(compiled_data.get('contracts', {}).keys())
                logger.error(f"Available contracts: {available_keys}")
                return Response(
                    err(f"Failed to extract contract info: {str(e)}"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update contract record with compiled ABI and bytecode
            contract.abi = contract_info["definition"]
            contract.bytecode = contract_info["contract"]
            contract.save()
            logger.info(f"✓ Updated contract {contract_id} in database")

            # Save compiled contract to JSON file in the required format
            # Use default constructor args (address zero) for Ethereum contracts
            default_constructor_args = ["0x0000000000000000000000000000000000000000"]
            json_output = {
                "contract": contract_info["contract"],  # bytecode
                "definition": contract_info["definition"],  # ABI
                "input": default_constructor_args  # default constructor args
            }

            json_file_path = os.path.join(file_path, f"{contract.name}.json")
            with open(json_file_path, "w") as json_file:
                json.dump(json_output, json_file, indent=2)
            logger.info(f"✓ Saved compiled contract JSON to: {json_file_path}")

            response_data = {
                "id": contract_id,
                "name": name,
                "abi": contract_info["definition"],  # 使用 definition 作为 abi
                "bytecode": contract_info["contract"],  # 使用 contract 作为 bytecode
            }

            return Response(ok(response_data), status=status.HTTP_200_OK)

        except Environment.DoesNotExist:
            logger.error("Environment not found")
            return Response(
                err("Environment not found"), status=status.HTTP_404_NOT_FOUND
            )
        except LoleidoOrganization.DoesNotExist:
            logger.error("Organization not found")
            return Response(
                err("Organization not found"), status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in Ethereum contract upload: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            # Clean up on failure
            if os.path.exists(file_path):
                os.system(f"rm -rf {file_path}")
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=EthereumContractUploadBody,
        responses=with_common_response(
            {status.HTTP_200_OK: EthereumContractUploadResponse}
        ),
    )
    @action(detail=False, methods=["post"])
    def upload(self, request, *args, **kwargs):
        """
        Upload a Solidity smart contract file without compilation.

        This endpoint accepts a .sol file and stores it for later compilation.
        Similar to the Fabric chaincode package functionality.

        :param request: Contains name, version, language, file, org_id
        :return: Uploaded contract ID and status
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Received Ethereum contract upload request")
        logger.info(f"Request data keys: {list(request.data.keys())}")
        logger.info(f"Request environment ID: {request.parser_context['kwargs'].get('environment_id')}")

        serializer = EthereumContractUploadBody(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(err(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get("name")
        version = serializer.validated_data.get("version")
        language = serializer.validated_data.get("language", "solidity")
        file = serializer.validated_data.get("file")
        org_id = serializer.validated_data.get("org_id")
        env_id = request.parser_context["kwargs"].get("environment_id")

        contract_id = make_uuid()

        try:
            # Validate environment exists
            # 检查环境类型，获取对应的模型实例
            try:
                # 首先尝试获取 EthEnvironment
                env = EthEnvironment.objects.get(id=env_id)
            except EthEnvironment.DoesNotExist:
                # 如果 EthEnvironment 不存在，尝试获取 Environment
                env = Environment.objects.get(id=env_id)

            org = LoleidoOrganization.objects.get(id=org_id)

            # Create storage directory
            file_path = os.path.join(ETHEREUM_CONTRACT_STORE, contract_id)
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            # Save the uploaded .sol file
            sol_file_path = os.path.join(file_path, file.name)
            with open(sol_file_path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)

            # Read contract content
            with open(sol_file_path, "r", encoding="utf-8") as f:
                contract_content = f.read()

            # Create contract record in database with 'uploaded' status
            contract_kwargs = {
                "id": contract_id,
                "name": name,
                "version": version,
                "language": language,
                "creator": org,
                "contract_content": contract_content,
                "filename": file.name,  # 保存文件名
            }
            # 根据环境类型设置正确的字段
            if isinstance(env, EthEnvironment):
                contract_kwargs["eth_environment"] = env
            else:
                contract_kwargs["environment"] = env

            contract = EthereumContract(**contract_kwargs)
            contract.save()

            response_data = {
                "id": contract_id,
                "name": name,
            }

            return Response(ok(response_data), status=status.HTTP_200_OK)

        except Environment.DoesNotExist:
            logger.error("Environment not found")
            return Response(
                err("Environment not found"), status=status.HTTP_404_NOT_FOUND
            )
        except LoleidoOrganization.DoesNotExist:
            logger.error("Organization not found")
            return Response(
                err("Organization not found"), status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in Ethereum contract upload: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            # Clean up on failure
            if os.path.exists(file_path):
                os.system(f"rm -rf {file_path}")
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="post",
        request_body=EthereumContractDeployBody,
        responses=with_common_response(
            {status.HTTP_200_OK: EthereumContractDeployResponse}
        ),
    )
    @action(detail=False, methods=["post"], url_path="deploy")
    def deploy(self, request, *args, **kwargs):
        """
        Deploy a compiled Ethereum smart contract to the blockchain using FireFly API.

        This endpoint deploys a previously compiled contract to an Ethereum network
        using FireFly's contract deployment API. The contract must be in 'compiled' status
        before deployment.

        URL: POST /namespaces/{ns}/contracts/deploy

        :param request: Contains contract_id, namespace, constructor_args
        :return: Deployed contract address and transaction hash
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Received Ethereum contract deploy request")
        logger.info(f"Request data: {request.data}")

        serializer = EthereumContractDeployBody(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            logger.error(f"Serializer validation failed: {serializer.errors}")
            return Response(err(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        contract_id = serializer.validated_data.get("contract_id")
        namespace = serializer.validated_data.get("namespace")
        constructor_args = serializer.validated_data.get("constructor_args", [])

        logger.info(f"Deploy params - contract_id: {contract_id}, namespace: {namespace}, constructor_args: {constructor_args}")

        try:
            # Retrieve the contract
            contract = EthereumContract.objects.get(id=contract_id)
            logger.info(f"Found contract: {contract.name}")

            # Validate that we have ABI and bytecode
            if not contract.abi or not contract.bytecode:
                logger.error("Contract ABI or bytecode is missing")
                return Response(
                    err("Contract ABI or bytecode is missing"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get environment ID from request context
            env_id = request.parser_context["kwargs"].get("environment_id")
            logger.info(f"Environment ID: {env_id}")

            # Get system node URL from EthNode
            from api.models import ResourceSet, EthNode, EthereumResourceSet
            from api.common.enums import EthNodeType

            # Get environment type (Ethereum or Fabric)
            try:
                env = EthEnvironment.objects.get(id=env_id)
                logger.info(f"Found EthEnvironment: {env.name}")
                resource_sets = ResourceSet.objects.filter(eth_environment=env)
            except EthEnvironment.DoesNotExist:
                logger.info("EthEnvironment not found, trying Environment")
                env = Environment.objects.get(id=env_id)
                logger.info(f"Found Environment: {env.name}")
                resource_sets = ResourceSet.objects.filter(environment=env)

            logger.info(f"Found {resource_sets.count()} resource sets")

            # Get EthereumResourceSet from ResourceSet
            ethereum_resource_sets = EthereumResourceSet.objects.filter(
                resource_set__in=resource_sets
            )
            logger.info(f"Found {ethereum_resource_sets.count()} ethereum resource sets")

            # Get EthNode of type 'system' from EthereumResourceSet
            system_nodes = EthNode.objects.filter(
                fabric_resource_set__in=ethereum_resource_sets,
                type=EthNodeType.System.value  # Filter by type='system'
            )
            logger.info(f"Found {system_nodes.count()} system nodes")

            if not system_nodes.exists():
                logger.error("No system nodes found for the environment")
                return Response(
                    err("No system nodes found for the environment"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use first available system node and get associated Firefly
            node = system_nodes.first()
            logger.info(f"Using system node: {node.name}")
            logger.info(f"Node type: {node.type}")

            # Get Firefly object through: EthNode → EthereumResourceSet → ResourceSet → Firefly
            ethereum_resource_set = node.fabric_resource_set
            if not ethereum_resource_set:
                logger.error(f"System node {node.name} has no ethereum resource set")
                return Response(
                    err("System node has no ethereum resource set"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            resource_set = ethereum_resource_set.resource_set
            if not resource_set:
                logger.error(f"Ethereum resource set {ethereum_resource_set.name} has no resource set")
                return Response(
                    err("Ethereum resource set has no resource set"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get Firefly instance associated with this ResourceSet
            firefly = Firefly.objects.filter(resource_set=resource_set).first()
            if not firefly:
                logger.error(f"No Firefly instance found for resource set {resource_set.id}")
                return Response(
                    err("No Firefly instance found for this environment"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(f"Found Firefly instance: {firefly.org_name}")
            firefly_core_url = firefly.core_url
            logger.info(f"Using FireFly URL: {firefly_core_url}")

            # Prepare constructor args - use default if not provided
            if not constructor_args or len(constructor_args) == 0:
                constructor_args = ["0x0000000000000000000000000000000000000000"]
                logger.info("Using default constructor_args: 0x0000000000000000000000000000000000000000")

            logger.info(f"Constructor args: {constructor_args}")

            # Prepare FireFly deployment request
            deployment_payload = {
                "contract": contract.bytecode,
                "definition": contract.abi,
                "input": constructor_args
            }

            # Call FireFly deploy API
            # Add confirm=true to wait for transaction confirmation
            deploy_url = f"http://{firefly_core_url}/api/v1/namespaces/{namespace}/contracts/deploy?confirm=true"
            logger.info(f"=== Deploying contract to FireFly ===")
            logger.info(f"Deploy URL: {deploy_url}")
            logger.info(f"Bytecode length: {len(contract.bytecode)} bytes")
            logger.info(f"ABI entries: {len(contract.abi)} functions/events")

            response = requests.post(
                deploy_url,
                headers={
                    "Content-Type": "application/json",
                    "Request-Timeout": "2m0s"  # 2 minute timeout
                },
                data=json.dumps(deployment_payload),
                timeout=120  # 2 minute timeout for requests library
            )

            logger.info(f"✓ FireFly response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body (complete): {response.text}")

            if response.status_code not in [200, 202]:  # Accept both sync and async responses
                logger.error(f"✗ FireFly deployment failed with status {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")  # Log only first 500 chars
                return Response(
                    err(f"FireFly deployment failed with status {response.status_code}"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Parse FireFly response
            deployment_result = response.json()

            # Check deployment status
            deployment_status = deployment_result.get("status", "Unknown")
            deployment_id = deployment_result.get("id")
            tx_id = deployment_result.get("tx")

            logger.info(f"Deployment status: {deployment_status}")
            logger.info(f"Deployment ID: {deployment_id}")
            logger.info(f"Transaction ID: {tx_id}")

            # Extract contract address and tx hash
            # FireFly returns contract address in output.contractLocation.address
            output_data = deployment_result.get("output", {})

            # Try to get contract address from contractLocation first
            contract_location = output_data.get("contractLocation", {})
            contract_address = contract_location.get("address")

            # Fallback to direct address field if contractLocation not present
            if not contract_address:
                contract_address = output_data.get("address")

            tx_hash = output_data.get("transactionHash")

            # Update contract with latest deployment information
            contract.contract_address = contract_address
            contract.deployment_tx_hash = tx_hash or tx_id
            contract.save()

            # Persist deployment history
            deployment_kwargs = {
                "contract": contract,
                "namespace": namespace,
                "constructor_args": constructor_args,
                "contract_address": contract_address,
                "deployment_tx_hash": tx_hash or tx_id,
                "deployment_id": deployment_id,
                "status": deployment_status,
            }
            if isinstance(env, EthEnvironment):
                deployment_kwargs["eth_environment"] = env
            else:
                deployment_kwargs["environment"] = env
            EthereumDeployment.objects.create(**deployment_kwargs)

            if deployment_status == "Succeeded" and contract_address:
                logger.info(f"✓ Contract deployed successfully")
                logger.info(f"  - Address: {contract_address}")
                logger.info(f"  - TxHash: {tx_hash or tx_id}")
            elif deployment_status == "Pending":
                logger.info(f"⏳ Contract deployment pending")
                logger.info(f"  - Transaction ID: {tx_id}")
            else:
                logger.warning(f"⚠ Deployment status: {deployment_status}")
                if not contract_address:
                    logger.warning(f"  - Contract address not available yet")

            response_data = {
                "contract_id": str(contract.id),
                "contract_address": contract_address,
                "transaction_hash": tx_hash or tx_id,
                "transaction_id": tx_id,
                "deployment_id": deployment_id,
                "status": deployment_status,
            }

            return Response(ok(response_data), status=status.HTTP_200_OK)

        except EthereumContract.DoesNotExist:
            logger.error(f"Contract not found: {contract_id}")
            return Response(
                err("Contract not found"), status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Unexpected error during deployment: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            traceback.print_exc()
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)
