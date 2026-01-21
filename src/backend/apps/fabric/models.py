"""Fabric domain models (stepwise migration, app_label pinned to api)."""

import os

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.enums import (
    FabricCAOrgType,
    NetworkType,
    FabricVersions,
    FabricCAServerType,
    FabricCAUserType,
    FabricCAUserStatus,
    NodeStatus,
    FabricNodeType,
)
from common.utils.common import make_uuid, random_name, hash_file
from django.conf import settings

MEDIA_ROOT = getattr(settings, "MEDIA_ROOT")
MIN_PORT = 1
MAX_PORT = 65535


class FabricResourceSet(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of organization",
        default=make_uuid,
        editable=True,
    )
    name = models.CharField(default="", max_length=64, help_text="Name of organization")
    created_at = models.DateTimeField(auto_now_add=True)
    msp = models.TextField(help_text="msp of organization", null=True)
    tls = models.TextField(help_text="tls of organization", null=True)
    network = models.ForeignKey(
        "Network",
        help_text="Network to which the organization belongs",
        null=True,
        related_name="organization",
        on_delete=models.SET_NULL,
    )
    org_type = models.CharField(
        choices=FabricCAOrgType.to_choices(True),
        max_length=32,
        help_text="Organization type",
    )
    resource_set = models.OneToOneField(
        "ResourceSet",
        help_text="Resource set to which the fabric resourceset belongs",
        null=False,
        related_name="sub_resource_set",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-created_at",)
        app_label = "api"


class Network(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of network",
        default=make_uuid,
        editable=True,
    )
    name = models.CharField(
        help_text="network name, can be generated automatically.",
        max_length=64,
        default=random_name("netowrk"),
    )
    type = models.CharField(
        help_text="Type of network, %s" % NetworkType.values(),
        max_length=64,
        default=NetworkType.Fabric.value,
    )
    version = models.CharField(
        help_text="""
    Version of network.
    Fabric supported versions: %s
    """
        % (FabricVersions.values()),
        max_length=64,
        default="",
    )
    created_at = models.DateTimeField(
        help_text="Create time of network", auto_now_add=True
    )
    consensus = models.CharField(
        help_text="Consensus of network",
        max_length=128,
        default="raft",
    )
    genesisblock = models.TextField(
        help_text="genesis block",
        null=True,
    )
    database = models.CharField(
        help_text="database of network",
        max_length=128,
        default="leveldb",
    )

    class Meta:
        ordering = ("-created_at",)
        app_label = "api"


def get_ca_certificate_path(instance, file):
    return os.path.join("fabric/ca/certificates/%s" % str(instance.id), file.name)


class FabricCA(models.Model):
    admin_name = models.CharField(
        help_text="Admin username for ca server",
        default="admin",
        max_length=32,
    )
    admin_password = models.CharField(
        help_text="Admin password for ca server",
        default="adminpw",
        max_length=32,
    )
    hosts = models.JSONField(
        help_text="Hosts for ca", null=True, blank=True, default=list
    )
    type = models.CharField(
        help_text="Fabric ca server type",
        default=FabricCAServerType.Signature.value,
        choices=FabricCAServerType.to_choices(),
        max_length=32,
    )
    node = models.ForeignKey(
        "Node",
        help_text="Node of ca",
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = "api"


class PeerCaUser(models.Model):
    user = models.ForeignKey(
        "NodeUser",
        help_text="User of ca node",
        null=True,
        on_delete=models.CASCADE,
    )
    username = models.CharField(
        help_text="If user not set, set username/password",
        max_length=64,
        default="",
    )
    password = models.CharField(
        help_text="If user not set, set username/password",
        max_length=64,
        default="",
    )
    type = models.CharField(
        help_text="User type of ca",
        max_length=64,
        choices=FabricCAUserType.to_choices(),
        default=FabricCAUserType.User.value,
    )
    peer_ca = models.ForeignKey(
        "PeerCa",
        help_text="Peer Ca configuration",
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = "api"


class PeerCa(models.Model):
    node = models.ForeignKey(
        "Node",
        help_text="CA node of peer",
        null=True,
        on_delete=models.CASCADE,
    )
    peer = models.ForeignKey(
        "FabricPeer",
        help_text="Peer node",
        null=True,
        on_delete=models.CASCADE,
    )
    address = models.CharField(
        help_text="Node Address of ca", default="", max_length=128
    )
    certificate = models.FileField(
        help_text="Certificate file for ca node.",
        max_length=256,
        upload_to=get_ca_certificate_path,
        blank=True,
        null=True,
    )
    type = models.CharField(
        help_text="Type of ca node for peer",
        choices=FabricCAServerType.to_choices(),
        max_length=64,
        default=FabricCAServerType.Signature.value,
    )

    class Meta:
        app_label = "api"


class FabricPeer(models.Model):
    name = models.CharField(help_text="Name of peer node", max_length=64, default="")
    gossip_use_leader_reflection = models.BooleanField(
        help_text="Gossip use leader reflection", default=True
    )
    gossip_org_leader = models.BooleanField(
        help_text="Gossip org leader", default=False
    )
    gossip_skip_handshake = models.BooleanField(
        help_text="Gossip skip handshake", default=True
    )
    local_msp_id = models.CharField(
        help_text="Local msp id of peer node", max_length=64, default=""
    )

    class Meta:
        app_label = "api"


class Node(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of node",
        default=make_uuid,
        editable=True,
    )
    name = models.CharField(help_text="Node name", max_length=64, default="")
    type = models.CharField(
        help_text="""
    Node type defined for network.
    Fabric available types: %s
    """
        % (FabricNodeType.names()),
        max_length=64,
    )
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
        FabricResourceSet,
        help_text="Organization of node",
        null=True,
        related_name="node",
        on_delete=models.CASCADE,
    )
    agent = models.ForeignKey(
        "Agent",
        help_text="Agent of node",
        null=True,
        related_name="node",
        on_delete=models.SET_NULL,
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
    config_file = models.TextField(
        help_text="Config file of node",
        null=True,
    )
    msp = models.TextField(
        help_text="msp of node",
        null=True,
    )
    tls = models.TextField(
        help_text="tls of node",
        null=True,
    )
    cid = models.CharField(
        help_text="id used in agent, such as container id",
        max_length=256,
        default="",
    )

    class Meta:
        ordering = ("-created_at",)
        app_label = "api"

    def get_compose_file_path(self):
        return "%s/org/%s/agent/docker/compose_files/%s/docker-compose.yml" % (
            MEDIA_ROOT,
            str(self.fabric_resource_set.id),
            str(self.id),
        )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        if self.name == "":
            self.name = random_name(self.type)
        super(Node, self).save(force_insert, force_update, using, update_fields)


class NodeUser(models.Model):
    name = models.CharField(help_text="User name of node", max_length=64, default="")
    secret = models.CharField(
        help_text="User secret of node", max_length=64, default=""
    )
    user_type = models.CharField(
        help_text="User type of node",
        choices=FabricCAUserType.to_choices(),
        default=FabricCAUserType.Peer.value,
        max_length=64,
    )
    node = models.ForeignKey(
        Node, help_text="Node of user", on_delete=models.CASCADE, null=True
    )
    status = models.CharField(
        help_text="Status of node user",
        choices=FabricCAUserStatus.to_choices(),
        default=FabricCAUserStatus.Registering.value,
        max_length=32,
    )
    attrs = models.CharField(
        help_text="Attributes of node user", default="", max_length=512
    )

    class Meta:
        ordering = ("id",)
        app_label = "api"


class Port(models.Model):
    node = models.ForeignKey(
        Node,
        help_text="Node of port",
        on_delete=models.CASCADE,
        null=True,
        related_name="port",
    )
    external = models.IntegerField(
        help_text="External port",
        default=0,
        validators=[MinValueValidator(MIN_PORT), MaxValueValidator(MAX_PORT)],
    )
    internal = models.IntegerField(
        help_text="Internal port",
        default=0,
        validators=[MinValueValidator(MIN_PORT), MaxValueValidator(MAX_PORT)],
    )
    eth_node = models.ForeignKey(
        "EthNode",
        help_text="Node of port",
        on_delete=models.CASCADE,
        null=True,
        related_name="ethport",
    )

    class Meta:
        ordering = ("external",)
        constraints = [
            models.UniqueConstraint(
                fields=("node", "internal"),
                name="unique_node_internal_port",
            ),
            models.UniqueConstraint(
                fields=("node", "external"),
                name="unique_node_external_port",
            ),
        ]
        app_label = "api"


class Channel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of channel",
        default=make_uuid,
        editable=True,
    )
    name = models.CharField(help_text="Name of channel", max_length=128, default="")
    resource_set = models.ForeignKey(
        "ResourceSet",
        help_text="Resource set which channel belongs to",
        null=True,
        on_delete=models.CASCADE,
        related_name="channel",
    )
    created_at = models.DateTimeField(
        help_text="Create time of channel", auto_now_add=True
    )
    genesisblock = models.TextField(
        help_text="genesis block",
        null=True,
    )
    anchorpeers = models.TextField(
        help_text="anchor peers",
        null=True,
    )
    status = models.CharField(
        help_text="Status of channel",
        max_length=32,
        default="active",
    )

    class Meta:
        ordering = ("-created_at",)
        app_label = "api"


class ResourceSet(models.Model):
    """
    Stand for a set of resource for some membership in a environment
    """

    id = models.UUIDField(
        primary_key=True,
        help_text="ID of midOrg",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.TextField(
        help_text="name of ResourceSet",
    )
    membership = models.ForeignKey(
        "Membership",
        help_text="related membership_id",
        null=False,
        on_delete=models.CASCADE,
    )
    environment = models.ForeignKey(
        "Environment",
        help_text="related environment_Id",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="resource_sets",
    )
    eth_environment = models.ForeignKey(
        "EthEnvironment",
        help_text="related eth_environment_Id",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="resource_sets",
    )
    agent = models.ForeignKey(
        "Agent",
        help_text="related agent_id",
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-id",)
        app_label = "api"


class FabricIdentity(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of fabric identity",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name_of_fabric_identity = models.CharField(
        help_text="name of fabric identity",
        default=None,
        max_length=128,
        null=False,
    )
    name_of_identity = models.CharField(
        help_text="name of identity",
        default=None,
        max_length=128,
        null=False,
    )
    secret_of_identity = models.CharField(
        help_text="secret of identity",
        default=None,
        max_length=128,
        null=False,
    )
    create_at = models.DateTimeField(
        help_text="create time of identity", auto_now_add=True
    )
    attributes = models.JSONField(
        help_text="attributes of identity", default=list, null=True, blank=True
    )
    resource_set = models.ForeignKey(
        "ResourceSet",
        help_text="related resource_set_id",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-create_at",)
        app_label = "api"


class ChainCode(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of ChainCode",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.CharField(help_text="name of chainCode", max_length=128)
    version = models.CharField(help_text="version of chainCode", max_length=128)
    creator = models.ForeignKey("LoLeidoOrganization", on_delete=models.CASCADE)
    language = models.CharField(help_text="language of chainCode", max_length=128)
    create_ts = models.DateTimeField(
        help_text="Create time of chainCode", auto_now_add=True
    )
    environment = models.ForeignKey(
        "Environment",
        help_text="environment of chainCode",
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = "api"


__all__ = [
    "FabricResourceSet",
    "Network",
    "FabricCA",
    "PeerCaUser",
    "PeerCa",
    "FabricPeer",
    "Node",
    "NodeUser",
    "Port",
    "Channel",
    "ResourceSet",
    "FabricIdentity",
    "ChainCode",
]
