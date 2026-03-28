#
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import shutil
import tarfile
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.dispatch import receiver
from django.db.models.signals import post_save
from requests import post

from common.enums import (
    HostStatus,
    HostType,
    K8SCredentialType,
    separate_upper_class,
    FileType,
)
from common.utils.common import make_uuid, random_agent_name, hash_file
from common.lib.firefly.api import register_identity
from apps.core.models import LoleidoOrganization

LOG = logging.getLogger(__name__)
from apps.fabric.models import FabricResourceSet, ResourceSet

LIMIT_K8S_CONFIG_FILE_MB = 100
LIMIT_FILE_MB = 100


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
        default=random_agent_name,
    )
    urls = models.URLField(help_text="Agent URL", null=True, blank=True)
    organization = models.ForeignKey(
        LoleidoOrganization,
        help_text="Organization of agent",
        null=True,
        related_name="agents",
        on_delete=models.SET_NULL,
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
        app_label = "api"


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
        on_delete=models.PROTECT,
        null=True,
    )

    class Meta:
        app_label = "api"


def get_file_path(instance, file):
    file_ext = file.split(".")[-1]
    filename = "%s.%s" % (hash_file(instance.file), file_ext)

    return os.path.join(
        "files/%s/%s" % (str(instance.organization.id), str(instance.id)),
        filename,
    )


def validate_file(file):
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
        app_label = "api"


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

    def register_to_firefly(self, key):
        """
        Register identity to FireFly (Fabric specific).
        """
        identity_id = register_identity(self.core_url, key, key, self.org_name)
        return identity_id or False

    def register_eth_identity_to_firefly(self, name, address):
        """
        Register Ethereum identity to FireFly (Ethereum specific).
        """
        identity_id = register_identity(self.core_url, name, address, self.org_name)
        return identity_id or False

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

    class Meta:
        app_label = "api"


class APISecretKey(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of APISecretKey",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    user = models.ForeignKey(
        "UserProfile",
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
        "Environment",
        help_text="related environment_id",
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
        help_text="Create time of APISecretKey", auto_now_add=True
    )

    def save(self, *args, **kwargs):
        import hashlib

        LOG.debug("APISecretKey hash update for user=%s", self.user_id)
        self.key_secret = hashlib.md5(self.key_secret.encode("utf-8")).hexdigest()
        super(APISecretKey, self).save(*args, **kwargs)

    def verifyKeySecret(self, key_secret):
        import hashlib

        LOG.debug("APISecretKey verify for user=%s", self.user_id)
        return self.key_secret == hashlib.md5(key_secret.encode("utf-8")).hexdigest()

    class Meta:
        app_label = "api"


class Oracle(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of Oracle",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.TextField(help_text="name of Oracle")
    environment = models.ForeignKey(
        "Environment",
        help_text="related environment_id",
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
        help_text="Create time of Oracle", auto_now_add=True
    )

    class Meta:
        app_label = "api"


class DmnEngine(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of DmnEngine",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    name = models.TextField(help_text="name of DmnEngine")
    environment = models.ForeignKey(
        "Environment",
        help_text="related environment_id",
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
        help_text="Create time of DmnEngine", auto_now_add=True
    )

    class Meta:
        app_label = "api"


__all__ = [
    "Agent",
    "KubernetesConfig",
    "File",
    "Firefly",
    "APISecretKey",
    "Oracle",
    "DmnEngine",
    "get_agent_config_file_path",
    "validate_agent_config_file",
    "get_file_path",
    "validate_file",
]
