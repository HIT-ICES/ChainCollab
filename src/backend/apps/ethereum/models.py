"""Ethereum domain models (stepwise migration, app_label pinned to api)."""

from django.db import models

from common.enums import FabricCAOrgType, NodeStatus, EthNodeType
from common.utils.common import make_uuid


class EthereumResourceSet(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of organization",
        default=make_uuid,
        editable=True,
    )
    name = models.CharField(default="", max_length=64, help_text="Name of organization")
    created_at = models.DateTimeField(auto_now_add=True)
    org_type = models.CharField(
        choices=FabricCAOrgType.to_choices(True),
        max_length=32,
        help_text="Organization type",
    )
    resource_set = models.OneToOneField(
        "ResourceSet",
        help_text="Resource set to which the ethereum resourceset belongs",
        null=True,
        related_name="ethereum_sub_resource_set",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-created_at",)
        app_label = "api"


class EthereumContract(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of Ethereum Contract",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.CharField(help_text="name of contract", max_length=128)
    version = models.CharField(help_text="version of contract", max_length=128)
    filename = models.CharField(
        help_text="Filename of the contract file",
        max_length=255,
        null=True,
        blank=True,
    )
    creator = models.ForeignKey("LoleidoOrganization", on_delete=models.CASCADE)
    language = models.CharField(
        help_text="language of contract", max_length=128, default="solidity"
    )
    create_ts = models.DateTimeField(
        help_text="Create time of contract", auto_now_add=True
    )
    environment = models.ForeignKey(
        "Environment",
        help_text="Fabric environment of contract",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    eth_environment = models.ForeignKey(
        "EthEnvironment",
        help_text="Ethereum environment of contract",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    abi = models.JSONField(
        help_text="Contract ABI (Application Binary Interface)",
        null=True,
        blank=True,
    )
    bytecode = models.TextField(
        help_text="Compiled contract bytecode",
        null=True,
        blank=True,
    )
    contract_content = models.TextField(
        help_text="Content of Solidity contract file",
        null=True,
        blank=True,
    )
    contract_address = models.CharField(
        help_text="Deployed contract address on blockchain",
        max_length=42,
        null=True,
        blank=True,
    )
    deployment_tx_hash = models.CharField(
        help_text="Transaction hash of contract deployment",
        max_length=66,
        null=True,
        blank=True,
    )
    status = models.CharField(
        help_text="Status of contract: compiled, deployed, failed",
        max_length=32,
        default="created",
    )

    class Meta:
        app_label = "api"


class EthereumDeployment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of Ethereum deployment",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    contract = models.ForeignKey(
        EthereumContract,
        help_text="related ethereum_contract_id",
        on_delete=models.CASCADE,
        related_name="deployments",
    )
    environment = models.ForeignKey(
        "Environment",
        help_text="Fabric environment of deployment (legacy)",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    eth_environment = models.ForeignKey(
        "EthEnvironment",
        help_text="Ethereum environment of deployment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    namespace = models.CharField(
        help_text="FireFly namespace for deployment",
        max_length=64,
        default="default",
    )
    constructor_args = models.JSONField(
        help_text="Constructor arguments used during deployment",
        null=True,
        blank=True,
    )
    contract_address = models.CharField(
        help_text="Deployed contract address on blockchain",
        max_length=42,
        null=True,
        blank=True,
    )
    deployment_tx_hash = models.CharField(
        help_text="Transaction hash of deployment",
        max_length=66,
        null=True,
        blank=True,
    )
    deployment_id = models.CharField(
        help_text="FireFly deployment request ID",
        max_length=128,
        null=True,
        blank=True,
    )
    status = models.CharField(
        help_text="Deployment status: Pending, Succeeded, Failed",
        max_length=32,
        default="Pending",
    )
    create_ts = models.DateTimeField(
        help_text="Create time of deployment", auto_now_add=True
    )

    class Meta:
        app_label = "api"


class IdentityDeployment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of identity contract deployment",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    eth_environment = models.OneToOneField(
        "EthEnvironment",
        help_text="related eth_environment id",
        related_name="identity_deployment",
        on_delete=models.CASCADE,
    )
    contract_name = models.CharField(
        help_text="identity contract name",
        max_length=128,
        default="IdentityRegistry",
    )
    contract_address = models.CharField(
        help_text="deployed contract address",
        max_length=66,
        null=True,
        blank=True,
    )
    deployment_tx_hash = models.CharField(
        help_text="deployment transaction hash",
        max_length=128,
        null=True,
        blank=True,
    )
    deployment_id = models.CharField(
        help_text="FireFly deployment request ID",
        max_length=128,
        null=True,
        blank=True,
    )
    interface_id = models.CharField(
        help_text="FireFly interface ID",
        max_length=128,
        null=True,
        blank=True,
    )
    api_id = models.CharField(
        help_text="FireFly API ID",
        max_length=128,
        null=True,
        blank=True,
    )
    api_name = models.CharField(
        help_text="FireFly API name",
        max_length=128,
        null=True,
        blank=True,
    )
    api_address = models.CharField(
        help_text="FireFly API address",
        max_length=256,
        null=True,
        blank=True,
    )
    firefly_listeners = models.JSONField(
        help_text="FireFly listeners registered for identity contract",
        null=True,
        blank=True,
    )
    status = models.CharField(
        help_text="status of identity deployment",
        max_length=32,
        default="NO",
    )
    error = models.TextField(
        help_text="deployment error message",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        help_text="create time of deployment", auto_now_add=True
    )
    updated_at = models.DateTimeField(
        help_text="update time of deployment", auto_now=True
    )

    class Meta:
        app_label = "api"


class EthereumIdentity(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of EthereumIdentity",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.TextField(help_text="name of EthereumIdentity")
    address = models.TextField(
        help_text="Ethereum address of identity",
        null=True,
        blank=True,
    )
    private_key = models.TextField(
        help_text="Private key of Ethereum identity",
        null=True,
        blank=True,
    )
    firefly_identity_id = models.TextField(
        help_text="firefly_identity_id of EthereumIdentity",
        null=True,
        blank=True,
    )
    eth_environment = models.ForeignKey(
        "EthEnvironment",
        help_text="related eth_environment_id",
        null=True,
        on_delete=models.CASCADE,
    )
    membership = models.ForeignKey(
        "Membership",
        help_text="related membership_id",
        null=True,
        on_delete=models.CASCADE,
    )
    create_at = models.DateTimeField(
        help_text="Create time of EthereumIdentity", auto_now_add=True
    )

    class Meta:
        verbose_name = "Ethereum Identity"
        verbose_name_plural = "Ethereum Identities"
        app_label = "api"


class EthNode(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of node",
        default=make_uuid,
        editable=True,
    )
    name = models.CharField(help_text="Node name", max_length=64, default="")
    urls = models.JSONField(
        help_text="URL configurations for node",
        null=True,
        blank=True,
        default=dict,
    )
    user = models.ForeignKey(
        "UserProfile",
        help_text="User of node",
        null=True,
        on_delete=models.CASCADE,
    )
    fabric_resource_set = models.ForeignKey(
        EthereumResourceSet,
        help_text="Organization of node",
        null=True,
        related_name="ethnode",
        on_delete=models.CASCADE,
    )
    agent = models.ForeignKey(
        "Agent",
        help_text="Agent of node",
        null=True,
        related_name="eth_nodes",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(
        help_text="Create time of network", auto_now_add=True
    )
    status = models.CharField(
        help_text="Status of node",
        choices=NodeStatus.to_choices(True),
        max_length=64,
        default=NodeStatus.Created.name.lower(),
    )
    type = models.CharField(
        help_text="""
    Node type defined for network.
    Ethereum available types: %s
    """
        % (EthNodeType.names()),
        max_length=64,
        null=True,
        blank=True,
    )
    sys_enode = models.TextField(
        help_text="System node enode URL (stored in system node) or bootnode enode (for org nodes)",
        null=True,
        blank=True,
    )
    cid = models.CharField(
        help_text="id used in agent, such as container id",
        max_length=256,
        default="",
    )

    class Meta:
        ordering = ("-created_at",)
        app_label = "api"


__all__ = [
    "EthereumResourceSet",
    "EthereumContract",
    "EthereumDeployment",
    "IdentityDeployment",
    "EthereumIdentity",
    "EthNode",
]
