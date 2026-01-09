#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework import serializers
from api.config import FABRIC_CHAINCODE_STORE
from api.models import EthereumContract
from api.common.serializers import ListResponseSerializer


class EthereumContractIDSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Ethereum Contract ID")


class EthereumContractUploadBody(serializers.Serializer):
    name = serializers.CharField(max_length=128, required=True, help_text="Contract name")
    version = serializers.CharField(max_length=128, required=True, help_text="Contract version")
    language = serializers.CharField(
        max_length=128,
        required=False,
        default="solidity",
        help_text="Contract language (default: solidity)"
    )
    file = serializers.FileField(help_text="Solidity contract file (.sol)")
    org_id = serializers.UUIDField(help_text="Organization ID", required=True)


class EthereumContractCompileBody(serializers.Serializer):
    name = serializers.CharField(max_length=128, required=True, help_text="Contract name")
    version = serializers.CharField(max_length=128, required=True, help_text="Contract version")
    language = serializers.CharField(
        max_length=128,
        required=False,
        default="solidity",
        help_text="Contract language (default: solidity)"
    )
    file = serializers.FileField(help_text="Solidity contract file (.sol)")
    org_id = serializers.UUIDField(help_text="Organization ID", required=True)


class EthereumContractDeployBody(serializers.Serializer):
    contract_id = serializers.UUIDField(help_text="Contract ID to deploy", required=True)
    namespace = serializers.CharField(
        max_length=128,
        required=True,
        help_text="Ethereum namespace/network identifier"
    )
    constructor_args = serializers.ListField(
        required=False,
        default=list,
        help_text="Constructor arguments for contract deployment"
    )


class EthereumContractResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(help_text="ID of Ethereum Contract")
    creator_name = serializers.CharField(source='creator.name', read_only=True)

    class Meta:
        model = EthereumContract
        fields = (
            "id",
            "name",
            "version",
            "creator_name",
            "language",
            "create_ts",
            "abi",
            "bytecode",
            "contract_address",
            "deployment_tx_hash",
            "status"
        )


class EthereumContractListResponse(ListResponseSerializer):
    data = EthereumContractResponseSerializer(many=True, help_text="Ethereum Contract data")


class EthereumContractCompileResponse(serializers.Serializer):
    id = serializers.UUIDField(help_text="Contract ID")
    name = serializers.CharField(help_text="Contract name")
    abi = serializers.JSONField(help_text="Contract ABI")
    bytecode = serializers.CharField(help_text="Contract bytecode")
    status = serializers.CharField(help_text="Compilation status")


class EthereumContractUploadResponse(serializers.Serializer):
    id = serializers.UUIDField(help_text="Contract ID")
    name = serializers.CharField(help_text="Contract name")
    status = serializers.CharField(help_text="Upload status")


class EthereumContractDeployResponse(serializers.Serializer):
    contract_id = serializers.UUIDField(help_text="Contract ID")
    contract_address = serializers.CharField(help_text="Deployed contract address")
    transaction_hash = serializers.CharField(help_text="Deployment transaction hash")
    status = serializers.CharField(help_text="Deployment status")
