import logging
import os
import re
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
from apps.core.routes.bpmn.serializers import (
    BpmnListSerializer,
    BpmnSerializer,
    BpmnInstanceSerializer,
    DmnSerializer,
)
import yaml
from apps.api.config import BASE_PATH, BPMN_CHAINCODE_STORE, CURRENT_IP, ETHEREUM_CONTRACT_STORE
from common import ok, err
from apps.core.models import BPMN, DMN, BPMNInstance
from apps.fabric.models import ChainCode
from apps.ethereum.models import EthereumContract
from apps.environment.models import Environment, EthEnvironment
from apps.core.models import LoleidoOrganization, Consortium
from zipfile import ZipFile
import json

# from api.routes.bpmn  import BpmnCreateBody
from rest_framework import viewsets, status
from requests import get, post


class BPMNViewsSet(viewsets.ModelViewSet):

    @action(methods=["post"], detail=False, url_path="_upload")
    def upload(self, request, pk=None, *args, **kwargs):
        try:
            consortiumid = request.data.get("consortiumid")
            orgid = request.data.get("orgid")
            name = request.data.get("name")
            bpmnContent = request.data.get("bpmnContent")
            svgContent = request.data.get("svgContent")
            raw_participants = request.data.get("participants")  # [P1,P2]
            participants = [
                {"id": recordkey, "name": raw_participants[recordkey]}
                for recordkey in raw_participants.keys()
            ]
            consortium = Consortium.objects.get(id=consortiumid)
            organization = LoleidoOrganization.objects.get(id=orgid)

            bpmn = BPMN(
                # consortium = consortium,
                organization=organization,
                consortium=consortium,
                name=name,
                svgContent=svgContent,
                bpmnContent=bpmnContent,
                participants=json.dumps(participants),
                status="Initiated",
            )

            bpmn.save()

            return Response(
                data=ok("bpmn file storaged success"), status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["get"], detail=False, url_path="_list")
    def list_all(self, request, pk=None, *args, **kwargs):
        try:
            bpmns = BPMN.objects.all()
            serializer = BpmnListSerializer(bpmns, many=True)
            return Response(data=ok(serializer.data), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        """
        更新Bpmn实例
        """
        try:
            bpmn = BPMN.objects.get(pk=pk)
            if "bpmn_id" in request.data:
                bpmn.bpmn_id = request.data.get("bpmn_id")
            if "name" in request.data:
                bpmn.name = request.data.get("name")
            if "status" in request.data:
                bpmn.status = request.data.get("status")
            if "user_id" in request.data:
                bpmn.user_id = request.data.get("user_id")
            if "firefly_url" in request.data:
                bpmn.firefly_url = request.data.get("firefly_url")
            if "envId" in request.data:
                envId = request.data.get("envId")
                envType = request.data.get("envType", "fabric")  # 默认为 fabric

                try:
                    if envType == "ethereum":
                        # 查询以太坊环境
                        eth_env = EthEnvironment.objects.get(pk=envId)
                        bpmn.eth_environment = eth_env
                        bpmn.environment = None
                    else:
                        # 查询 Fabric 环境
                        env = Environment.objects.get(pk=envId)
                        bpmn.environment = env
                        bpmn.eth_environment = None
                except (Environment.DoesNotExist, EthEnvironment.DoesNotExist):
                    return Response(
                        data=err(f"Environment with id {envId} and type {envType} does not exist"),
                        status=status.HTTP_404_NOT_FOUND
                    )
            if "events" in request.data:
                bpmn.events = request.data.get("events")
            if "ethereum_contract_id" in request.data:
                ethereum_contract_id = request.data.get("ethereum_contract_id")
                try:
                    ethereum_contract = EthereumContract.objects.get(pk=ethereum_contract_id)
                    bpmn.ethereum_contract = ethereum_contract
                except EthereumContract.DoesNotExist:
                    return Response(
                        data=err(f"Ethereum contract with id {ethereum_contract_id} does not exist"),
                        status=status.HTTP_404_NOT_FOUND
                    )

            bpmn.save()
            serializer = BpmnSerializer(bpmn)
            return Response(data=ok(serializer.data), status=status.HTTP_202_ACCEPTED)
        except BPMN.DoesNotExist:
            return Response(
                data=err(f"BPMN with id {pk} does not exist"),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Bpmn详情
        """
        try:
            bpmn = BPMN.objects.get(pk=pk)
        except BPMN.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = BpmnSerializer(bpmn)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        获取Bpmn列表
        """
        try:
            bpmns = BPMN.objects.all()
            serializer = BpmnSerializer(bpmns, many=True)
            return Response(ok(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    def _zip_folder(self, folder_path, output_path):
        with ZipFile(output_path, "w") as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, folder_path))

    @action(methods=["post"], detail=True, url_path="package")
    def package(self, request, pk, *args, **kwargs):
        try:
            bpmn_id = pk
            orgid = request.data.get("orgId")
            chaincodeContent = request.data.get("chaincodeContent")
            ffiContent = request.data.get("ffiContent")
            bpmn = BPMN.objects.get(pk=bpmn_id)
            env_id = bpmn.environment.id

            with open(
                BPMN_CHAINCODE_STORE + "/chaincode-go-bpmn/chaincode/smartcontract.go",
                "w",
                encoding="utf-8",
            ) as file:
                file.write(chaincodeContent)

            self._zip_folder(
                BPMN_CHAINCODE_STORE, BASE_PATH + "/opt/bpmn_chaincode.zip"
            )

            headers = request.headers
            files = {
                "file": open(file=BASE_PATH + "/opt//bpmn_chaincode.zip", mode="rb")
            }
            response = post(
                f"http://{CURRENT_IP}:8000/api/v1/environments/{env_id}/chaincodes/package",
                data={
                    "name": bpmn.name.replace(".bpmn", ""),
                    "version": 1,
                    "language": "golang",
                    "org_id": orgid,
                },
                files=files,
                headers={"Authorization": headers["Authorization"]},
            )
            chaincode_id = response.json()["data"]["id"]
            chaincode = ChainCode.objects.get(id=chaincode_id)

            bpmn.ffiContent = ffiContent
            bpmn.chaincode_content = chaincodeContent
            bpmn.chaincode = chaincode
            bpmn.status = "Generated"
            # consortium = consortium,
            bpmn.save()

            return Response(
                data=ok("bpmn file storaged success"), status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=True, url_path="upload-eth")
    def upload_eth(self, request, pk, *args, **kwargs):
        """
        Upload Ethereum contract for BPMN (similar to Fabric package).
        This endpoint accepts either:
        1. contractId - references an existing contract
        2. contractContent - creates a new contract from the provided code
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Received upload-eth request for BPMN: {pk}")
        logger.info(f"Request data: {request.data}")
        logger.info(f"Request kwargs: {request.parser_context['kwargs']}")

        try:
            bpmn_id = pk
            orgid = request.data.get("orgId")
            contract_id = request.data.get("contractId")
            contract_content = request.data.get("contractContent")

            logger.info(f"Org ID: {orgid}, Contract ID: {contract_id}, Has contract content: {bool(contract_content)}")

            bpmn = BPMN.objects.get(pk=bpmn_id)
            logger.info(f"BPMN found: {bpmn.name}")
            logger.info(f"BPMN environment: {bpmn.environment}")
            logger.info(f"BPMN eth_environment: {bpmn.eth_environment}")

            # 获取当前环境ID
            # 尝试从请求上下文中获取环境ID，或者从请求参数中获取
            env_id = request.parser_context["kwargs"].get("environment_id")
            if not env_id:
                # 如果没有直接获取到环境ID，检查是否有eth_environment关联
                env_id = bpmn.eth_environment.id if bpmn.eth_environment else None

            if not env_id:
                # 检查是否有fabric环境关联，以太坊环境可能使用相同的字段
                env_id = bpmn.environment.id if bpmn.environment else None

            logger.info(f"Resolved env_id: {env_id}")

            if not env_id:
                logger.error("No environment associated with BPMN")
                return Response(
                    err("BPMN is not associated with any environment"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prepare the upload request to Ethereum API
            headers = request.headers

            # 确定环境类型和API前缀
            env_prefix = "eth-environments"  # 默认使用eth-environments前缀
            try:
                # 尝试确定环境类型
                if EthEnvironment.objects.filter(id=env_id).exists():
                    env_prefix = "eth-environments"
                elif Environment.objects.filter(id=env_id).exists():
                    env_prefix = "environments"
            except Exception as e:
                logger.error(f"Error checking environment type: {str(e)}")

            # 如果提供了合约内容，需要先将其保存为临时文件再上传
            if contract_content:
                import tempfile

                # 使用BPMN名称作为合约文件名
                contract_filename = bpmn.name.replace(".bpmn", ".sol")

                # 创建临时文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(contract_content)
                    temp_file_path = temp_file.name

                logger.info(f"Created temporary contract file: {temp_file_path}")

                try:
                    # 上传合约文件到 ethereum API
                    with open(temp_file_path, 'rb') as file_obj:
                        files = {"file": (contract_filename, file_obj, 'text/plain')}
                        response = post(
                            f"http://{CURRENT_IP}:8000/api/v1/{env_prefix}/{env_id}/contracts/upload",
                            data={
                                "name": bpmn.name.replace(".bpmn", ""),
                                "version": "1.0",
                                "language": "solidity",
                                "org_id": orgid,
                            },
                            files=files,
                            headers={"Authorization": headers["Authorization"]},
                        )
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

                if response.status_code != 200:
                    logger.error(f"Failed to upload contract: {response.text}")
                    return Response(
                        err(f"Failed to upload contract: {response.text}"),
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 从响应中获取创建的合约ID
                contract_id = response.json()["data"]["id"]
                logger.info(f"Contract uploaded successfully with ID: {contract_id}")

            else:
                # 如果没有提供合约内容，使用已有的contractId
                if not contract_id:
                    logger.error("Neither contractId nor contractContent provided")
                    return Response(
                        err("Either contractId or contractContent must be provided"),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                logger.info(f"Using existing contract ID: {contract_id}")

            # 获取上传后的合约对象
            eth_contract = EthereumContract.objects.get(id=contract_id)

            # Update BPMN with contract information
            bpmn.chaincode_content = eth_contract.contract_content  # Reuse existing field for contract content
            bpmn.ethereum_contract = eth_contract  # 设置 ethereum_contract 字段
            bpmn.status = "Generated"
            bpmn.save()

            logger.info(f"BPMN updated with contract ID: {contract_id}")

            return Response(
                data=ok({
                    "message": "Ethereum contract uploaded successfully",
                    "contract_id": contract_id
                }),
                status=status.HTTP_202_ACCEPTED
            )

        except BPMN.DoesNotExist:
            logger.error(f"BPMN not found: {pk}")
            return Response(err("BPMN not found"), status=status.HTTP_404_NOT_FOUND)
        except LoleidoOrganization.DoesNotExist:
            logger.error("Organization not found")
            return Response(err("Organization not found"), status=status.HTTP_404_NOT_FOUND)
        except EthereumContract.DoesNotExist:
            logger.error(f"Contract not found: {contract_id}")
            return Response(err("Contract not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in upload_eth for BPMN {pk}: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["post"], detail=True, url_path="compile-eth")
    def compile_eth(self, request, pk, *args, **kwargs):
        """
        Compile Ethereum contract for BPMN.
        This endpoint saves the contract content and calls the Ethereum compile API.
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Received compile-eth request for BPMN: {pk}")
        logger.info(f"Request data: {request.data}")
        logger.info(f"Request kwargs: {request.parser_context['kwargs']}")

        try:
            bpmn_id = pk
            orgid = request.data.get("orgId")
            contract_id = request.data.get("contractId")  # 接受 contractId，但优先使用 bpmn 关联的合约

            logger.info(f"Org ID: {orgid}, Contract ID from request: {contract_id}")

            bpmn = BPMN.objects.get(pk=bpmn_id)
            logger.info(f"BPMN found: {bpmn.name}")
            logger.info(f"BPMN environment: {bpmn.environment}")
            logger.info(f"BPMN eth_environment: {bpmn.eth_environment}")

            # 优先使用 bpmn 关联的合约，如果没有则使用请求中的 contractId
            if bpmn.ethereum_contract:
                eth_contract = bpmn.ethereum_contract
                logger.info(f"Using BPMN associated contract: {eth_contract.id}")
            elif contract_id:
                eth_contract = EthereumContract.objects.get(pk=contract_id)
                logger.info(f"Using request contract: {contract_id}")
            else:
                logger.error("No contract associated with BPMN and no contractId provided")
                return Response(
                    err("No contract associated with BPMN and no contractId provided"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            contract_content = eth_contract.contract_content
            contract_name = eth_contract.filename or f"{eth_contract.name}.sol"  # 使用原始文件名，如果没有则使用合约名称

            # 获取当前环境ID
            # 尝试从请求上下文中获取环境ID，或者从请求参数中获取
            env_id = request.parser_context["kwargs"].get("environment_id")
            if not env_id:
                # 如果没有直接获取到环境ID，检查是否有eth_environment关联
                env_id = bpmn.eth_environment.id if bpmn.eth_environment else None

            if not env_id:
                # 检查是否有fabric环境关联，以太坊环境可能使用相同的字段
                env_id = bpmn.environment.id if bpmn.environment else None

            logger.info(f"Resolved env_id: {env_id}")

            if not env_id:
                logger.error("No environment associated with BPMN")
                return Response(
                    err("BPMN is not associated with any environment"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save contract content to a temporary file
            # 使用已存储的合约文件进行编译，而不是字符串
            # 合约文件已在上传时保存到 ETHEREUM_CONTRACT_STORE/{contract_id}/ 目录下
            contract_file_path = os.path.join(ETHEREUM_CONTRACT_STORE, str(eth_contract.id), eth_contract.filename)

            if not os.path.exists(contract_file_path):
                logger.error(f"Contract file not found: {contract_file_path}")
                return Response(
                    err("Contract file not found"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Compiling contract from file: {contract_file_path}")

            # Prepare the compile request to Ethereum API
            headers = request.headers

            # 确定环境类型和API前缀
            env_prefix = "eth-environments"  # 默认使用eth-environments前缀
            try:
                # 尝试确定环境类型
                if EthEnvironment.objects.filter(id=env_id).exists():
                    env_prefix = "eth-environments"
                elif Environment.objects.filter(id=env_id).exists():
                    env_prefix = "environments"
            except Exception as e:
                logger.error(f"Error checking environment type: {str(e)}")

            with open(contract_file_path, 'rb') as file_obj:
                files = {"file": (eth_contract.filename, file_obj, 'text/plain')}
                response = post(
                    f"http://{CURRENT_IP}:8000/api/v1/{env_prefix}/{env_id}/contracts/compile",
                    data={
                        "name": bpmn.name.replace(".bpmn", ""),
                        "version": "1.0",
                        "language": "solidity",
                        "org_id": orgid,
                        "contract_id": str(eth_contract.id),  # 传递已有合约ID
                    },
                    files=files,
                    headers={"Authorization": headers["Authorization"]},
                )

            if response.status_code != 200:
                logger.error(f"Failed to compile contract: {response.text}")
                return Response(
                    err(f"Failed to compile contract: {response.text}"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 获取编译结果
            compile_result = response.json()["data"]

            # 刷新合约对象以获取最新数据
            eth_contract.refresh_from_db()
            logger.info(f"Contract {eth_contract.id} compiled successfully")

            # Update BPMN with contract information
            bpmn.chaincode_content = contract_content  # Reuse existing field for contract content
            bpmn.ethereum_contract = eth_contract  # 确保 ethereum_contract 字段已设置
            bpmn.status = "Compiled"  # 编译成功后状态更新为Compiled
            bpmn.save()

            return Response(
                data=ok({
                    "message": "Ethereum contract compiled successfully",
                    "contract_id": str(eth_contract.id),
                    "abi": compile_result.get("abi"),
                    "bytecode": compile_result.get("bytecode")
                }),
                status=status.HTTP_202_ACCEPTED
            )

        except BPMN.DoesNotExist:
            logger.error(f"BPMN not found: {pk}")
            return Response(err("BPMN not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in compile_eth for BPMN {pk}: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)


class BPMNInstanceViewSet(viewsets.ModelViewSet):

    def create(self, request, *args, **kwargs):
        """
        创建Bpmn实例
        """
        try:
            bpmn_id = request.parser_context["kwargs"].get("bpmn_id")
            bpmn = BPMN.objects.get(pk=bpmn_id)
            instance_chaincode_id = request.data.get("instance_chaincode_id")
            name = request.data.get("name")
            bpmn_instance = BPMNInstance.objects.create(
                bpmn=bpmn, instance_chaincode_id=instance_chaincode_id, name=name
            )
            bpmn_instance.save()
            serializer = BpmnInstanceSerializer(bpmn_instance)
            return Response(data=ok(serializer.data), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Bpmn实例详情
        """
        try:
            bpmn_instance = BPMNInstance.objects.get(pk=pk)
            serializer = BpmnInstanceSerializer(bpmn_instance)
            return Response(serializer.data)
        except BPMNInstance.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def list(self, request, *args, **kwargs):
        """
        获取Bpmn实例列表
        """
        try:
            bpmn_id = request.parser_context["kwargs"].get("bpmn_id")
            try:
                bpmn = BPMN.objects.get(pk=bpmn_id)
            except BPMN.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            bpmn_instances = BPMNInstance.objects.filter(bpmn=bpmn)
            serializer = BpmnInstanceSerializer(bpmn_instances, many=True)
            return Response(ok(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    def _ends_with_time_format(self, input_string):
        pattern = r"^test-\d{4}-\d{2}-\d{2}-\d{2}\.\d{2}\.\d{2}\.bpmn$"
        if re.match(pattern, input_string):
            return True
        else:
            return False

    def _ends_with_Test(self, input_string):
        pattern = r".*Test.bpmn$"
        if re.match(pattern, input_string):
            return True
        return False


class DmnViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        """
        创建Dmn实例
        """
        try:
            consortiumid = request.data.get("consortiumid")
            orgid = request.data.get("orgid")
            consortium = Consortium.objects.get(id=consortiumid)
            organization = LoleidoOrganization.objects.get(id=orgid)
            dmn = DMN.objects.create(
                consortium=consortium,
                organization=organization,
                name=request.data.get("name"),
                dmnContent=request.data.get("dmnContent"),
                svgContent=request.data.get("svgContent"),
            )
            dmn.save()
            serializer = DmnSerializer(dmn)
            return Response(data=ok(serializer.data), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Dmn详情
        """
        try:
            dmn = DMN.objects.get(pk=pk)
        except DMN.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = DmnSerializer(dmn)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        获取Dmn列表
        """
        try:
            dmns = DMN.objects.all()
            serializer = DmnSerializer(dmns, many=True)
            return Response(ok(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        """
        更新Dmn实例
        """
        try:
            dmn = DMN.objects.get(pk=pk)
            if "dmn_id" in request.data:
                dmn.dmn_id = request.data.get("dmn_id")
            if "name" in request.data:
                dmn.name = request.data.get("name")
            if "dmnContent" in request.data:
                dmn.dmnContent = request.data.get("dmnContent")
            if "dmnSvgContent" in request.data:
                dmn.dmnSvgContent = request.data.get("dmnSvgContent")
            if "consortiumid" in request.data:
                dmn.consortiumid = request.data.get("consortiumid")
            if "orgid" in request.data:
                dmn.orgid = request.data.get("orgid")

            dmn.save()
            serializer = DmnSerializer(dmn)
            return Response(data=ok(serializer.data), status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response(err(str(e)), status=status.HTTP_400_BAD_REQUEST)
