#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import os
import re
import tarfile
import traceback
import logging
import shutil
import zipfile

logger = logging.getLogger(__name__)
DEPLOY_TIMEOUT_SECONDS = int(os.environ.get("FIREFLY_CONTRACT_DEPLOY_TIMEOUT_SECONDS", "300"))
FIXED_SOLC_VERSION = os.environ.get("ETHEREUM_FIXED_SOLC_VERSION", "0.8.19")

from drf_yasg.utils import swagger_auto_schema
from apps.api.config import ETHEREUM_CONTRACT_STORE
from apps.ethereum.models import EthereumContract, EthereumDeployment
from apps.environment.models import Environment
from apps.core.models import LoleidoOrganization
from common.utils.common import make_uuid
from common.serializers import PageQuerySerializer
from common.utils.common import with_common_response
from common.exceptions import ResourceNotFound

from apps.ethereum.routes.ethereum.serializers import (
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

from common import ok, err
from common.lib.ethereum.solc_compiler import SolidityCompiler
from common.lib.ethereum.contract_actions import ensure_contract_actions
from common.lib.ethereum.firefly_contracts import deploy_contract as firefly_deploy_contract
import requests
import json
from apps.infra.models import Firefly
from apps.environment.models import EthEnvironment

class EthereumContractViewSet(viewsets.ViewSet):
    """Class represents Ethereum Contract related operations."""

    permission_classes = [
        IsAuthenticated,
    ]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _safe_extract_path(self, target_root: str, member_name: str) -> str:
        normalized = os.path.normpath(member_name).replace("\\", "/")
        if normalized.startswith("../") or normalized == ".." or os.path.isabs(normalized):
            raise ValueError(f"Unsafe archive entry: {member_name}")
        return os.path.join(target_root, normalized)

    def _extract_archive(self, archive_path: str, target_root: str) -> None:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    destination = self._safe_extract_path(target_root, member.filename)
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    with archive.open(member) as src, open(destination, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            return
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as archive:
                for member in archive.getmembers():
                    if not member.isfile():
                        continue
                    destination = self._safe_extract_path(target_root, member.name)
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    src = archive.extractfile(member)
                    if src is None:
                        continue
                    with src, open(destination, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            return
        raise ValueError("Unsupported archive format. Use .zip/.tar/.tgz/.tar.gz")

    def _list_solidity_files(self, root_dir: str) -> list[str]:
        solidity_files: list[str] = []
        for root, _, files in os.walk(root_dir):
            for filename in files:
                if filename.endswith(".sol"):
                    solidity_files.append(os.path.join(root, filename))
        return sorted(solidity_files)

    def _resolve_source_entry(self, root_dir: str, requested_contract_name: str | None = None) -> str:
        solidity_files = self._list_solidity_files(root_dir)
        if not solidity_files:
            raise FileNotFoundError("No Solidity source found in uploaded file")
        if requested_contract_name:
            exact_name = f"{requested_contract_name}.sol"
            exact_matches = [
                path for path in solidity_files if os.path.basename(path) == exact_name
            ]
            if exact_matches:
                return exact_matches[0]
        preferred_names = {"chaincode.sol", "contract.sol"}
        preferred_matches = [
            path for path in solidity_files if os.path.basename(path).lower() in preferred_names
        ]
        if preferred_matches:
            return preferred_matches[0]
        if len(solidity_files) == 1:
            return solidity_files[0]
        return solidity_files[0]

    def _resolve_compiled_contract_name(self, compiled_data: dict, requested_contract_name: str | None = None) -> str:
        contracts = compiled_data.get("contracts", {})
        deployable = [key for key, value in contracts.items() if value.get("bin")]
        if not deployable:
            raise ValueError("No deployable contract found in compilation output")
        deployable_names = [key.split(":")[-1] for key in deployable]
        if requested_contract_name:
            matches = [
                key for key in deployable
                if key.split(":")[-1] == requested_contract_name
                or key.split(":")[-1].lower() == requested_contract_name.lower()
            ]
            if matches:
                return matches[0].split(":")[-1]
            if len(deployable_names) == 1:
                logger.warning(
                    "Requested contract name '%s' not found; falling back to sole deployable contract '%s'",
                    requested_contract_name,
                    deployable_names[0],
                )
                return deployable_names[0]
            raise ValueError(
                f"Contract '{requested_contract_name}' not found in compilation output. "
                f"Available contracts: {', '.join(deployable_names)}"
            )
        if len(deployable_names) == 1:
            return deployable_names[0]
        return deployable_names[0]

    def _resolve_firefly_for_env(self, env_id: str):
        from apps.fabric.models import ResourceSet
        from apps.ethereum.models import EthNode, EthereumResourceSet
        from common.enums import EthNodeType

        try:
            env = EthEnvironment.objects.get(id=env_id)
            resource_sets = ResourceSet.objects.filter(eth_environment=env)
        except EthEnvironment.DoesNotExist:
            env = Environment.objects.get(id=env_id)
            resource_sets = ResourceSet.objects.filter(environment=env)

        ethereum_resource_sets = EthereumResourceSet.objects.filter(resource_set__in=resource_sets)
        system_nodes = EthNode.objects.filter(
            fabric_resource_set__in=ethereum_resource_sets,
            type=EthNodeType.System.value,
        )
        if not system_nodes.exists():
            raise ValueError("No system nodes found for the environment")
        node = system_nodes.first()
        ethereum_resource_set = node.fabric_resource_set
        if not ethereum_resource_set or not ethereum_resource_set.resource_set:
            raise ValueError("System node has no resource set")
        resource_set = ethereum_resource_set.resource_set
        firefly = Firefly.objects.filter(resource_set=resource_set).first()
        if not firefly:
            raise ValueError("No Firefly instance found for this environment")
        return env, firefly

    def _normalize_abi(self, abi: object) -> list[dict]:
        if isinstance(abi, str):
            try:
                abi = json.loads(abi)
            except Exception as exc:
                raise ValueError(f"Invalid ABI JSON: {exc}") from exc
        if not isinstance(abi, list):
            raise ValueError("Compiled ABI is not a list")
        return abi

    def _validate_constructor_args(self, abi: list[dict], constructor_args: list) -> None:
        constructor = next(
            (entry for entry in abi if isinstance(entry, dict) and entry.get("type") == "constructor"),
            None,
        )
        if not constructor:
            if constructor_args:
                raise ValueError("This contract does not define a constructor. Remove constructor arguments.")
            return

        inputs = constructor.get("inputs") or []
        expected_count = len(inputs)
        actual_count = len(constructor_args)
        if expected_count != actual_count:
            expected_signature = ", ".join(
                [f"{item.get('name') or 'arg'}:{item.get('type') or 'unknown'}" for item in inputs]
            ) or "no arguments"
            raise ValueError(
                f"Constructor args mismatch. Expected {expected_count} argument(s): {expected_signature}. Got {actual_count}."
            )

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific Ethereum contract by ID.

        :param request: HTTP request
        :return: Contract details
        """
        try:
            contract_id = request.parser_context["kwargs"].get("pk")
            contract = EthereumContract.objects.get(id=contract_id)
            latest_deployment = contract.deployments.order_by("-create_ts").first()
            contract_data = {
                "id": contract.id,
                "name": contract.name,
                "version": contract.version,
                "filename": contract.filename,
                "creator": contract.creator.name,
                "language": contract.language,
                "create_ts": contract.create_ts,
                "status": contract.status,
                "contract_address": contract.contract_address,
                "deployment_tx_hash": contract.deployment_tx_hash,
                "contract_content": contract.contract_content,
                "deployment": {
                    "id": str(latest_deployment.id),
                    "namespace": latest_deployment.namespace,
                    "constructor_args": latest_deployment.constructor_args,
                    "deployment_id": latest_deployment.deployment_id,
                    "status": latest_deployment.status,
                    "create_ts": latest_deployment.create_ts,
                } if latest_deployment else None,
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
            contracts = EthereumContract.objects.filter(eth_environment_id=env_id).order_by("-create_ts")

            contracts_list = [
                {
                    "id": contract.id,
                    "name": contract.name,
                    "version": contract.version,
                    "creator": contract.creator.name,
                    "language": contract.language,
                    "create_ts": contract.create_ts,
                    "filename": contract.filename,
                    "status": contract.status,
                    "contract_address": contract.contract_address,
                    "deployment_tx_hash": contract.deployment_tx_hash,
                }
                for contract in contracts
            ]
            return Response(data=contracts_list, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="install")
    def install(self, request, *args, **kwargs):
        env_id = request.parser_context["kwargs"].get("environment_id")
        name = str(request.data.get("name") or "").strip()
        version = str(request.data.get("version") or "").strip()
        language = str(request.data.get("language") or "solidity").strip() or "solidity"
        org_id = request.data.get("org_id")
        requested_compiler_version = str(request.data.get("compiler_version") or "").strip() or None
        requested_contract_name = str(request.data.get("contract_name") or "").strip() or None
        namespace = str(request.data.get("namespace") or "default").strip() or "default"
        constructor_args = request.data.get("constructor_args") or []
        uploaded_file = request.FILES.get("file") or request.FILES.get("archive")

        if not name:
            return Response(err("name is required"), status=status.HTTP_400_BAD_REQUEST)
        if not version:
            return Response(err("version is required"), status=status.HTTP_400_BAD_REQUEST)
        if not org_id:
            return Response(err("org_id is required"), status=status.HTTP_400_BAD_REQUEST)
        if not uploaded_file:
            return Response(err("file is required"), status=status.HTTP_400_BAD_REQUEST)
        if requested_contract_name and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", requested_contract_name):
            return Response(
                err("Invalid contract_name. Use letters, numbers and underscores, and start with a letter or underscore."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(constructor_args, str):
            try:
                constructor_args = json.loads(constructor_args)
            except Exception:
                return Response(err("constructor_args must be a JSON array"), status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(constructor_args, list):
            return Response(err("constructor_args must be a JSON array"), status=status.HTTP_400_BAD_REQUEST)

        contract_id = make_uuid()
        file_path = os.path.join(ETHEREUM_CONTRACT_STORE, str(contract_id))
        source_root = os.path.join(file_path, "src")

        try:
            env, firefly = self._resolve_firefly_for_env(env_id)
            org = LoleidoOrganization.objects.get(id=org_id)

            os.makedirs(file_path, exist_ok=True)
            os.makedirs(source_root, exist_ok=True)

            upload_name = os.path.basename(getattr(uploaded_file, "name", "contract.sol"))
            upload_path = os.path.join(file_path, upload_name)
            with open(upload_path, "wb") as handle:
                for chunk in uploaded_file.chunks():
                    handle.write(chunk)

            if upload_name.lower().endswith(".sol"):
                source_path = os.path.join(source_root, upload_name)
                shutil.copyfile(upload_path, source_path)
            else:
                self._extract_archive(upload_path, source_root)
                source_path = self._resolve_source_entry(source_root, requested_contract_name)

            with open(source_path, "r", encoding="utf-8") as source_handle:
                contract_content = source_handle.read()

            contract = EthereumContract.objects.create(
                id=contract_id,
                name=name,
                version=version,
                filename=os.path.relpath(source_path, file_path).replace("\\", "/"),
                creator=org,
                language=language,
                eth_environment=env if isinstance(env, EthEnvironment) else None,
                environment=env if isinstance(env, Environment) else None,
                contract_content=contract_content,
                status="uploaded",
            )

            compiler = SolidityCompiler(version=FIXED_SOLC_VERSION)
            is_installed, version_or_error = compiler.check_installation()
            if not is_installed:
                return Response(
                    err(f"Solidity compiler not available: {version_or_error}"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            output_json_path = os.path.join(file_path, f"{name}.compiled.json")
            return_code, compiled_data, error_msg = compiler.compile_contract(
                source_path,
                output_json_path,
            )
            if return_code != 0:
                return Response(err(f"Compilation failed: {error_msg}"), status=status.HTTP_400_BAD_REQUEST)

            from common.lib.ethereum.convert_contract import extract_contract_info

            compiled_contract_name = self._resolve_compiled_contract_name(
                compiled_data,
                requested_contract_name=requested_contract_name,
            )
            contract_info = extract_contract_info(
                compiled_data,
                contract_name=compiled_contract_name,
                constructor_params=constructor_args,
            )

            normalized_abi = self._normalize_abi(contract_info["definition"])
            self._validate_constructor_args(normalized_abi, constructor_args)

            contract.abi = normalized_abi
            contract.bytecode = contract_info["contract"]
            contract.status = "compiled"
            contract.save(update_fields=["abi", "bytecode", "status", "contract_content", "updated_at"] if hasattr(contract, "updated_at") else ["abi", "bytecode", "status", "contract_content"])

            logger.info(
                "Deploying Ethereum contract via FireFly core=%s namespace=%s contract=%s constructor_args=%s",
                firefly.core_url,
                namespace,
                requested_contract_name or compiled_contract_name,
                constructor_args,
            )
            try:
                deployment_result = firefly_deploy_contract(
                    firefly.core_url,
                    contract.abi,
                    contract.bytecode,
                    namespace=namespace,
                    constructor_args=constructor_args,
                    confirm=True,
                    timeout=DEPLOY_TIMEOUT_SECONDS,
                )
            except RuntimeError as exc:
                contract.status = "failed"
                contract.save(update_fields=["status"])
                logger.error("FireFly deployment failed for contract %s: %s", contract.id, exc)
                return Response(
                    err(f"FireFly deployment failed: {exc}"),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            deployment_status = deployment_result.get("status", "Unknown")
            deployment_id = deployment_result.get("id")
            tx_id = deployment_result.get("tx")
            output_data = deployment_result.get("output", {})
            contract_location = output_data.get("contractLocation", {})
            contract_address = contract_location.get("address") or output_data.get("address")
            tx_hash = output_data.get("transactionHash") or tx_id

            contract.contract_address = contract_address
            contract.deployment_tx_hash = tx_hash
            contract.status = "deployed" if contract_address else "compiled"
            contract.save(update_fields=["contract_address", "deployment_tx_hash", "status"])

            EthereumDeployment.objects.create(
                contract=contract,
                namespace=namespace,
                constructor_args=constructor_args,
                contract_address=contract_address,
                deployment_tx_hash=tx_hash,
                deployment_id=deployment_id,
                status=deployment_status,
                eth_environment=env if isinstance(env, EthEnvironment) else None,
                environment=env if isinstance(env, Environment) else None,
            )

            try:
                ensure_contract_actions(
                    firefly.core_url,
                    contract.abi,
                    requested_contract_name or compiled_contract_name,
                    file_path,
                    namespace=namespace,
                    logger=logger,
                )
            except Exception as exc:
                logger.warning(f"Contract actions generation failed: {str(exc)}")

            return Response(
                ok(
                    {
                        "contract_id": str(contract.id),
                        "name": contract.name,
                        "contract_name": requested_contract_name or compiled_contract_name,
                        "compiler_version": FIXED_SOLC_VERSION,
                        "contract_address": contract_address,
                        "transaction_hash": tx_hash,
                        "deployment_id": deployment_id,
                        "status": deployment_status,
                    }
                ),
                status=status.HTTP_200_OK,
            )
        except LoleidoOrganization.DoesNotExist:
            return Response(err("Organization not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in Ethereum contract install: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            if os.path.exists(file_path):
                shutil.rmtree(file_path, ignore_errors=True)
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

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
            compiler = SolidityCompiler(version=FIXED_SOLC_VERSION)

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
            from common.lib.ethereum.convert_contract import extract_contract_info
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
            from apps.fabric.models import ResourceSet
            from apps.ethereum.models import EthNode, EthereumResourceSet
            from common.enums import EthNodeType

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

            try:
                contract_dir = os.path.join(ETHEREUM_CONTRACT_STORE, contract_id)
                actions_path = ensure_contract_actions(
                    firefly_core_url,
                    contract.abi,
                    contract.name or "Contract",
                    contract_dir,
                    namespace=namespace,
                    logger=logger,
                )
                logger.info(f"✓ Contract actions saved: {actions_path}")
            except Exception as e:
                logger.warning(f"Contract actions generation failed: {str(e)}")

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
        if requested_compiler_version and requested_compiler_version != FIXED_SOLC_VERSION:
            logger.warning(
                "Ignoring requested compiler version %s, fixed Solidity version is %s",
                requested_compiler_version,
                FIXED_SOLC_VERSION,
            )
