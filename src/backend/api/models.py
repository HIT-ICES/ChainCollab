#
# SPDX-License-Identifier: Apache-2.0
#
import os
import shutil
import tarfile
from unittest.util import _MAX_LENGTH
from zipfile import ZipFile
from requests import get, post
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.postgres.fields import ArrayField
from api.common.enums import FabricCAEnrollType, FabricCARegisterType, FabricCAOrgType
import json

from api.common.enums import (
    HostStatus,
    HostType,
    K8SCredentialType,
    separate_upper_class,
    NodeStatus,
    FileType,
    FabricCAServerType,
    FabricCAUserType,
    FabricCAUserStatus,
)
from api.common.enums import (
    UserRole,
    NetworkType,
    FabricNodeType,
    FabricVersions,
)
from api.utils.common import make_uuid, random_name, hash_file
from api.config import CELLO_HOME

SUPER_USER_TOKEN = getattr(settings, "ADMIN_TOKEN", "")
MAX_CAPACITY = getattr(settings, "MAX_AGENT_CAPACITY", 100)
MAX_NODE_CAPACITY = getattr(settings, "MAX_NODE_CAPACITY", 600)
MEDIA_ROOT = getattr(settings, "MEDIA_ROOT")
LIMIT_K8S_CONFIG_FILE_MB = 100
# Limit file upload size less than 100Mb
LIMIT_FILE_MB = 100
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
    resource_set = models.ForeignKey(
        "ResourceSet",
        help_text="Resource set to which the fabric resourceset belongs",
        null=True,
        related_name="sub_resource_set",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ("-created_at",)


class UserProfile(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of user",
        default=make_uuid,
        editable=True,
    )
    email = models.EmailField(db_index=True, unique=True)
    username = models.CharField(default="", max_length=64, help_text="Name of user")
    role = models.CharField(
        choices=UserRole.to_choices(True),
        default=UserRole.User.value,
        max_length=64,
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User Info"
        verbose_name_plural = verbose_name
        ordering = ["-date_joined"]

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == UserRole.Admin.name.lower()

    @property
    def is_operator(self):
        return self.role == UserRole.Operator.name.lower()

    @property
    def is_common_user(self):
        return self.role == UserRole.User.name.lower()


def get_agent_config_file_path(instance, file):
    file_ext = file.split(".")[-1]
    filename = "%s.%s" % (hash_file(instance.config_file), file_ext)

    return os.path.join("config_files/%s" % str(instance.id), filename)


def validate_agent_config_file(file):
    file_size = file.size
    if file_size > LIMIT_K8S_CONFIG_FILE_MB * 1024 * 1024:
        raise ValidationError("Max file size is %s MB" % LIMIT_K8S_CONFIG_FILE_MB)


class Agent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of agent",
        default=make_uuid,
        editable=True,
    )
    name = models.CharField(
        help_text="Agent name, can be generated automatically.",
        max_length=64,
        default=random_name("agent"),
    )
    urls = models.URLField(help_text="Agent URL", null=True, blank=True)
    # resource_set = models.ForeignKey(
    #     "ResourceSet",
    #     null=True,
    #     on_delete=models.CASCADE,
    #     help_text="Organization of agent",
    #     related_name="agent",
    # )
    organization = models.ForeignKey(
        "LoleidoOrganization",
        help_text="Organization of agent",
        null=True,
        related_name="agents",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        help_text="Status of agent",
        choices=HostStatus.to_choices(True),
        max_length=10,
        default=HostStatus.Active.name.lower(),
    )
    type = models.CharField(
        help_text="Type of agent",
        choices=HostType.to_choices(True),
        max_length=32,
        default=HostType.Docker.name.lower(),
    )
    config_file = models.FileField(
        help_text="Config file for agent",
        max_length=256,
        blank=True,
        upload_to=get_agent_config_file_path,
    )
    created_at = models.DateTimeField(
        help_text="Create time of agent", auto_now_add=True
    )

    # free_port = models.IntegerField(
    #     help_text="Agent free port.",
    #     default=30000,
    # )
    free_ports = ArrayField(
        models.IntegerField(blank=True), help_text="Agent free ports.", null=True
    )

    def delete(self, using=None, keep_parents=False):
        if self.config_file:
            if os.path.isfile(self.config_file.path):
                os.remove(self.config_file.path)
                shutil.rmtree(
                    os.path.dirname(self.config_file.path), ignore_errors=True
                )

        super(Agent, self).delete(using, keep_parents)

    class Meta:
        ordering = ("-created_at",)


@receiver(post_save, sender=Agent)
def extract_file(sender, instance, created, *args, **kwargs):
    if created:
        if instance.config_file:
            file_format = instance.config_file.name.split(".")[-1]
            if file_format in ["tgz", "gz"]:
                tar = tarfile.open(instance.config_file.path)
                tar.extractall(path=os.path.dirname(instance.config_file.path))
            elif file_format == "zip":
                with ZipFile(instance.config_file.path, "r") as zip_file:
                    zip_file.extractall(path=os.path.dirname(instance.config_file.path))


class KubernetesConfig(models.Model):
    credential_type = models.CharField(
        help_text="Credential type of k8s",
        choices=K8SCredentialType.to_choices(separate_class_name=True),
        max_length=32,
        default=separate_upper_class(K8SCredentialType.CertKey.name),
    )
    enable_ssl = models.BooleanField(
        help_text="Whether enable ssl for api", default=False
    )
    ssl_ca = models.TextField(
        help_text="Ca file content for ssl", default="", blank=True
    )
    nfs_server = models.CharField(
        help_text="NFS server address for k8s",
        default="",
        max_length=256,
        blank=True,
    )
    parameters = models.JSONField(
        help_text="Extra parameters for kubernetes",
        default=dict,
        null=True,
        blank=True,
    )
    cert = models.TextField(help_text="Cert content for k8s", default="", blank=True)
    key = models.TextField(help_text="Key content for k8s", default="", blank=True)
    username = models.CharField(
        help_text="Username for k8s credential",
        default="",
        max_length=128,
        blank=True,
    )
    password = models.CharField(
        help_text="Password for k8s credential",
        default="",
        max_length=128,
        blank=True,
    )
    agent = models.ForeignKey(
        Agent,
        help_text="Agent of kubernetes config",
        on_delete=models.CASCADE,
        null=True,
    )


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


def get_compose_file_path(instance, file):
    return os.path.join(
        "org/%s/agent/docker/compose_files/%s"
        % (str(instance.organization.id), str(instance.id)),
        "docker-compose.yml",
    )


def get_ca_certificate_path(instance, file):
    return os.path.join("fabric/ca/certificates/%s" % str(instance.id), file.name)


def get_node_file_path(instance, file):
    """
    Get the file path where will be stored in
    :param instance: database object of this db record
    :param file: file object.
    :return: path of file system which will store the file.
    """
    file_ext = file.split(".")[-1]
    filename = "%s.%s" % (hash_file(instance.file), file_ext)

    return os.path.join(
        "files/%s/node/%s" % (str(instance.organization.id), str(instance.id)),
        filename,
    )


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
        UserProfile,
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
        Agent,
        help_text="Agent of node",
        null=True,
        related_name="node",
        on_delete=models.CASCADE,
    )
    # network = models.ForeignKey(
    #     Network,
    #     help_text="Network which node joined.",
    #     on_delete=models.CASCADE,
    #     null=True,
    # )
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

    # def delete(self, using=None, keep_parents=False):
    #     if self.compose_file:
    #         compose_file_path = Path(self.compose_file.path)
    #         if os.path.isdir(os.path.dirname(compose_file_path)):
    #             shutil.rmtree(os.path.dirname(compose_file_path))
    #
    #     # remove related files of node
    #     if self.file:
    #         file_path = Path(self.file.path)
    #         if os.path.isdir(os.path.dirname(file_path)):
    #             shutil.rmtree(os.path.dirname(file_path))
    #
    #     if self.ca:
    #         self.ca.delete()
    #
    #     super(Node, self).delete(using, keep_parents)


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

    class Meta:
        ordering = ("external",)


def get_file_path(instance, file):
    """
    Get the file path where will be stored in
    :param instance: database object of this db record
    :param file: file object.
    :return: path of file system which will store the file.
    """
    file_ext = file.split(".")[-1]
    filename = "%s.%s" % (hash_file(instance.file), file_ext)

    return os.path.join(
        "files/%s/%s" % (str(instance.organization.id), str(instance.id)),
        filename,
    )


def validate_file(file):
    """
    Validate file of upload
    :param file: file object
    :return: raise exception if validate failed
    """
    file_size = file.size
    if file_size > LIMIT_FILE_MB * 1024 * 1024:
        raise ValidationError("Max file size is %s MB" % LIMIT_FILE_MB)


class File(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of file",
        default=make_uuid,
        editable=True,
    )
    organization = models.ForeignKey(
        FabricResourceSet,
        help_text="Organization of file",
        null=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(help_text="File name", max_length=64, default="")
    file = models.FileField(
        help_text="File", max_length=256, blank=True, upload_to=get_file_path
    )
    created_at = models.DateTimeField(
        help_text="Create time of agent", auto_now_add=True
    )
    type = models.CharField(
        choices=FileType.to_choices(True),
        max_length=32,
        help_text="File type",
        default=FileType.Certificate.name.lower(),
    )

    class Meta:
        ordering = ("-created_at",)

    # class User(models.Model):
    #     id = models.UUIDField(
    #         primary_key=True,
    #         help_text="ID of user",
    #         default=make_uuid,
    #         editable=True,
    #     )
    #     name = models.CharField(
    #         help_text="user name", max_length=128
    #     )
    #     roles = models.CharField(
    #         help_text="roles of user", max_length=128
    #     )
    #     organization = models.ForeignKey(
    #         "Organization", on_delete=models.CASCADE)
    #     attributes = models.CharField(
    #         help_text="attributes of user", max_length=128
    #     )
    #     revoked = models.CharField(
    #         help_text="revoked of user", max_length=128
    #     )
    #     create_ts = models.DateTimeField(
    #         help_text="Create time of user", auto_now_add=True
    #     )
    #     msp = models.TextField(
    #         help_text="msp of user",
    #         null=True,
    #     )
    #     tls = models.TextField(
    #         help_text="tls of user",
    #         null=True,
    #     )


class Channel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of Channel",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.CharField(help_text="name of channel", max_length=128)
    fabric_resource_set = models.ManyToManyField(
        to="FabricResourceSet",
        help_text="the organization of the channel",
        related_name="channels",
        # on_delete=models.SET_NULL
    )
    create_ts = models.DateTimeField(
        help_text="Create time of Channel", auto_now_add=True
    )
    network = models.ForeignKey("Network", on_delete=models.CASCADE)
    orderers = models.ManyToManyField(
        to="Node",
        help_text="Orderer list in the channel",
    )
    config = models.JSONField(
        help_text="Channel config",
        default=dict,
        null=True,
        blank=True,
    )

    def get_channel_config_path(self):
        return "/var/www/server/" + self.name + "_config.block"

    def get_channel_artifacts_path(self, artifact):
        return (
            CELLO_HOME
            + "/"
            + self.network.name
            + "/channel-artifacts/"
            + self.name
            + "_"
            + artifact
        )


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


# new Model


class Environment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of environment",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.TextField(help_text="name of environment")
    create_at = models.DateTimeField(
        help_text="create time of environment", auto_now_add=True
    )
    consortium = models.ForeignKey(
        "Consortium",
        help_text="consortium of environment",
        null=True,
        on_delete=models.CASCADE,
    )
    network = models.ForeignKey(Network, null=True, on_delete=models.DO_NOTHING)
    status = models.CharField(
        help_text="status of environment,can be CREATED|INITIALIZED|STARTED|ACTIVATED|FIREFLY",
        max_length=32,
        default="CREATED",
    )
    create_at = models.DateTimeField(
        help_text="create time of environment", auto_now_add=True
    )


class LoleidoOrganization(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of LoleidoOrganization",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.TextField(help_text="name of LoleidoOrganization")
    members = models.ManyToManyField(
        UserProfile,
        help_text="related user_id",
        through="LoleidoMemebership",
        related_name="orgs",
    )


class LoleidoMemebership(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of LoleidoMemebership",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    loleido_organization = models.ForeignKey(
        LoleidoOrganization,
        help_text="related loleido_organization_id",
        null=False,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        UserProfile,
        help_text="related user_id",
        null=False,
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        help_text="role of LoleidoMemebership",
        default="Member",
        max_length=32,
        choices=(("Member", "Member"), ("Admin", "Admin"), ("Owner", "Owner")),
    )

    class Meta:
        unique_together = ("loleido_organization", "user")


class Consortium(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of Consortium",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    orgs = models.ManyToManyField(
        LoleidoOrganization,
        help_text="related loleido_organization_id",
        through="Membership",
        related_name="consortiums",
    )
    name = models.TextField(
        help_text="name of Consortium",
    )


class Membership(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of membership",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    loleido_organization = models.ForeignKey(
        LoleidoOrganization,
        help_text="related loleido_organization_id",
        null=False,
        on_delete=models.CASCADE,
    )
    consortium = models.ForeignKey(
        Consortium,
        help_text="related consortium_id",
        null=False,
        on_delete=models.CASCADE,
    )
    name = models.TextField(help_text="name of membership")
    create_at = models.DateTimeField(
        help_text="create time of membership", auto_now_add=True
    )
    primary_contact_email = models.EmailField(
        help_text="primary contact email of membership",
        null=True,
    )


class ResourceSet(models.Model):
    """
    Stand for a set of resource for some memebership in a environment
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
        Membership,
        help_text="related membership_id",
        null=False,
        on_delete=models.CASCADE,
    )
    environment = models.ForeignKey(
        Environment,
        help_text="related environment_Id",
        null=False,
        on_delete=models.CASCADE,
        related_name="resource_sets",
    )
    agent = models.ForeignKey(
        Agent,
        help_text="related agent_id",
        null=True,
        on_delete=models.SET_NULL,
    )


class Firefly(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of firefly",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    org_name = models.CharField(help_text="org name of firefly", max_length=128)
    resource_set = models.ForeignKey(
        ResourceSet,
        help_text="related resource_set id",
        null=False,
        on_delete=models.CASCADE,
        related_name="firefly",
    )
    core_url = models.TextField(
        help_text="name of core url",
    )
    sandbox_url = models.TextField(
        help_text="name of sandbox url",
    )
    fab_connect_url = models.TextField(
        help_text="name of fabconnect url",
        blank=True,
        null=True,
    )
    # to add fab_connect_address

    def register_certificate(self, name, attributes, type="client", maxEnrollments=-1):
        if attributes is None:
            attributes = []
        fab_connect_address = f"http://{self.fab_connect_url}/identities"
        response = post(
            fab_connect_address,
            data=json.dumps(
                {
                    "name": name,
                    "attributes": attributes,
                    "type": type,
                    "maxEnrollments": maxEnrollments,
                }
            ),
        )
        # print(response.json())
        return response.json()["name"], response.json()["secret"]

    def enroll_certificate(self, name, secret, attributes):
        fab_connect_address = f"http://{self.fab_connect_url}/identities/{name}/enroll"
        response = post(
            fab_connect_address,
            data=json.dumps(
                {"secret": secret, "attributes": {k: True for k in attributes}}
            ),
        )
        return response.json()["success"]

    def register_to_firefly(self, key):
        org_name = self.org_name
        address = f"http://{self.core_url}/api/v1/identities"
        print(self.core_url, address, org_name, key)
        print(org_name, key)
        response = post(
            address,
            data=json.dumps({"parent": org_name, "key": key, "name": key}),
            headers={"Content-Type": "application/json"},
        )
        print({"parent": org_name, "key": key, "name": key})
        print(response.json())
        return response.json().get("id", False)

    # def invoke_chaincode(self, ):
    #     address = f"http://{self.core_url}/api/v1/chaincodes/{name}/invoke"
    #     response = post(address, data={"args": args})
    #     # TO MODIFY
    #     return response.json()


class UserPreference(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of userPreference",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    user = models.ForeignKey(
        UserProfile,
        help_text="related user_id",
        null=False,
        on_delete=models.CASCADE,
    )
    last_active_environment = models.ForeignKey(
        Environment,
        help_text="related environment_id",
        null=True,
        on_delete=models.SET_NULL,
    )
    last_active_consortium = models.ForeignKey(
        Consortium,
        help_text="related consortium_id",
        null=True,
        on_delete=models.SET_NULL,
    )
    last_active_organization = models.ForeignKey(
        ResourceSet,
        help_text="related middle_org_id",
        null=True,
        on_delete=models.SET_NULL,
    )


class LoleidoOrgJoinConsortiumInvitation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of loleidoOrgJoinConsortiumInvite",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    invitor = models.ForeignKey(
        LoleidoOrganization,
        help_text="related loleido_organization_id",
        default=None,
        null=False,
        on_delete=models.CASCADE,
        related_name="sended_invitations",
    )
    loleido_organization = models.ForeignKey(
        LoleidoOrganization,
        help_text="related loleido_organization_id",
        null=False,
        on_delete=models.CASCADE,
    )
    consortium = models.ForeignKey(
        Consortium,
        help_text="related consortium_id",
        null=False,
        on_delete=models.CASCADE,
    )
    role = models.TextField(
        help_text="role of loleidoOrgJoinConsortiumInvite", default="Member"
    )
    message = models.TextField(
        help_text="message of loleidoOrgJoinConsortiumInvite",
    )
    status = models.CharField(
        help_text="status of LoleidoOrgJoinConsortiumInvite",
        default="pending",
        max_length=32,
        choices=(
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ),
    )
    create_at = models.DateTimeField(
        help_text="Create time of loleidoOrgJoinConsortiumInvite", auto_now_add=True
    )


class UserJoinOrgInvitation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of userJoinOrgInvite",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    user = models.ForeignKey(
        UserProfile,
        help_text="related user_id",
        null=False,
        on_delete=models.CASCADE,
    )
    loleido_organization = models.ForeignKey(
        LoleidoOrganization,
        help_text="related loleido_organization_id",
        null=False,
        on_delete=models.CASCADE,
    )
    role = models.TextField(help_text="role of userJoinOrgInvite", default="Member")
    message = models.TextField(
        help_text="message of userJoinOrgInvite",
    )
    status = models.CharField(
        help_text="status of userJoinOrgInvite",
        default="pending",
        max_length=32,
        choices=(
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ),
    )
    create_at = models.DateTimeField(
        help_text="Create time of userJoinOrgInvite", auto_now_add=True
    )
    invitor = models.ForeignKey(
        UserProfile,
        help_text="related user_id",
        default=None,
        null=True,
        on_delete=models.CASCADE,
        related_name="sended_invitations",
    )


class BPMN(models.Model):
    # //ChainCodeID
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of userJoinOrgInvite",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    consortium = models.ForeignKey(
        Consortium,
        help_text="related consortium_id",
        null=True,
        on_delete=models.CASCADE,
    )

    organization = models.ForeignKey(
        LoleidoOrganization,
        help_text="related organization_id",
        null=False,
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        help_text="status of BPMN",
        default="pending",
        max_length=32,
        choices=(
            ("Initiated", "Initiated"),
            ("DeployEnved", "DeployEnved"),
            ("Generated", "Generated"),
            ("Installed", "Installed"),
            ("Registered", "Registered"),
        ),
    )
    name = models.CharField(
        help_text="Name of Bpmn",
        max_length=255,
        null=True,
        blank=True,
    )
    participants = models.TextField(
        help_text="participants of BpmnStoragedFile",
        null=True,
        blank=True,
    )
    events = models.TextField(
        help_text="events of BpmnStoragedFile",
        null=True,
        blank=True,
    )

    bpmnContent = models.TextField(help_text="content of bpmn file")
    svgContent = models.TextField(help_text="content of svg file")
    # create_at = models.DateTimeField(
    #     help_text="Create time of BpmnStoragedFile", auto_now_add=True
    # )
    # chaincode_content = models.TextField(
    #     help_text="content of chaincode file", null=True, blank=True, default=None
    # )
    chaincode = models.ForeignKey(
        ChainCode,
        help_text="related chaincode_id",
        null=True,
        on_delete=models.CASCADE,
    )
    chaincode_content = models.TextField(
        help_text="content of chaincode file",
        null=True,
        blank=True,
        default=None,
    )
    firefly_url = models.TextField(
        help_text="firefly url of BPMNInstance",
        null=True,
        blank=True,
    )
    ffiContent = models.TextField(
        help_text="content of ffi file", null=True, blank=True, default=None
    )
    environment = models.ForeignKey(
        Environment,
        help_text="related environment_id",
        null=True,
        on_delete=models.CASCADE,
    )


class BPMNInstance(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of BPMNInstance",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.CharField(
        help_text="Name of BPMNInstance",
        max_length=255,
        null=True,
        blank=True,
    )
    instance_id = models.IntegerField(
        help_text="instance_id of BPMNInstance",
        null=True,
        blank=True,
    )
    bpmn = models.ForeignKey(
        BPMN,
        help_text="related bpmn_id",
        null=False,
        on_delete=models.CASCADE,
    )
    # status = models.CharField(
    #     help_text="status of BPMNInstance",
    #     default="pending",
    #     max_length=32,
    #     choices=(
    #         ("Initiated", "Initiated"),
    #         ("Fullfilled", "Fullfilled"),
    #         ("Generated", "Generated"),
    #         ("Installed", "Installed"),
    #         ("Registered", "Registered"),
    #     ),
    # )
    create_at = models.DateTimeField(
        help_text="Create time of BPMNInstance", auto_now_add=True
    )
    update_at = models.DateTimeField(
        help_text="Update time of BPMNInstance", auto_now=True
    )


class BpmnParticipantBindingRecord(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of BPMNBindingRecord",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    bpmn_instance = models.ForeignKey(
        BPMNInstance,
        help_text="related bpmn_instance_id",
        null=False,
        on_delete=models.CASCADE,
    )
    participant_id = models.CharField(
        help_text="ID of participant",
        max_length=255,
        null=True,
        blank=True,
    )
    membership = models.ForeignKey(
        Membership,
        help_text="related membership_id",
        null=False,
        on_delete=models.CASCADE,
    )


class BpmnDmnBindingRecord(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of BPMNBindingRecord",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    bpmn_instance = models.ForeignKey(
        BPMNInstance,
        help_text="related bpmn_instance_id",
        null=False,
        on_delete=models.CASCADE,
    )
    business_rule_id = models.CharField(
        help_text="ID of business rule",
        max_length=255,
        null=True,
        blank=True,
    )
    dmn_instance_id = models.CharField(
        help_text="ID of dmn",
        max_length=255,
        null=True,
        blank=True,
    )


class DMN(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of Dmn",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.CharField(
        help_text="Name of Dmn",
        max_length=255,
        null=True,
        blank=True,
    )
    consortium = models.ForeignKey(
        Consortium,
        help_text="related consortium_id",
        null=True,
        on_delete=models.CASCADE,
    )

    organization = models.ForeignKey(
        LoleidoOrganization,
        help_text="related organization_id",
        null=False,
        on_delete=models.CASCADE,
    )
    dmnContent = models.TextField(help_text="content of dmn file")
    svgContent = models.TextField(help_text="content of dmn`s svg file")


class APISecretKey(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of APISecretKey",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    user = models.ForeignKey(
        UserProfile,
        help_text="related user_id",
        null=False,
        on_delete=models.CASCADE,
    )
    key = models.CharField(
        help_text="key of APISecretKey",
        max_length=255,
        null=True,
        blank=True,
    )
    # key secret will be hashed before save
    key_secret = models.CharField(
        help_text="key_secret of APISecretKey",
        max_length=255,
        null=True,
        blank=True,
    )
    environment = models.ForeignKey(
        Environment,
        help_text="related environment_id",
        null=True,
        on_delete=models.CASCADE,
    )
    membership = models.ForeignKey(
        Membership,
        help_text="related membership_id",
        null=True,
        on_delete=models.CASCADE,
    )
    create_at = models.DateTimeField(
        help_text="Create time of APISecretKey", auto_now_add=True
    )

    def save(self, *args, **kwargs):
        import hashlib

        print("START")
        print(self.key_secret)
        print(hashlib.md5(self.key_secret.encode("utf-8")).hexdigest())
        print("END")
        self.key_secret = hashlib.md5(self.key_secret.encode("utf-8")).hexdigest()
        super(APISecretKey, self).save(*args, **kwargs)

    def verifyKeySecret(self, key_secret):
        import hashlib

        print(key_secret)
        print(hashlib.md5(key_secret.encode("utf-8")).hexdigest())
        return self.key_secret == hashlib.md5(key_secret.encode("utf-8")).hexdigest()


class FabricIdentity(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of FabricIdentity",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.TextField(help_text="name of FabricIdentity")
    signer = models.TextField(
        help_text="signer of FabricIdentity",
        null=True,
        blank=True,
    )
    secret = models.TextField(
        help_text="secret of FabricIdentity",
        null=True,
        blank=True,
    )
    firefly_identity_id = models.TextField(
        help_text="firefly_identity_id of FabricIdentity",
        null=True,
        blank=True,
    )
    environment = models.ForeignKey(
        Environment,
        help_text="related environment_id",
        null=True,
        on_delete=models.CASCADE,
    )
    membership = models.ForeignKey(
        Membership,
        help_text="related membership_id",
        null=True,
        on_delete=models.CASCADE,
    )
    create_at = models.DateTimeField(
        help_text="Create time of FabricIdentity", auto_now_add=True
    )

    def save(self, *args, **kwargs):
        import hashlib

        self.secret = hashlib.md5(self.secret.encode("utf-8")).hexdigest()
        super(FabricIdentity, self).save(*args, **kwargs)

    def verifySecret(self, secret):
        import hashlib

        return self.secret == hashlib.md5(secret.encode("utf-8")).hexdigest()
