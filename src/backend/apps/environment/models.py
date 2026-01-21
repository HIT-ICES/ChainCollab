"""Environment domain models (stepwise migration, app_label pinned to api)."""

from django.db import models

from common.utils.common import make_uuid


class Task(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of task",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    type = models.CharField(
        help_text="Task type",
        max_length=64,
    )
    status = models.CharField(
        help_text="Task status: PENDING, RUNNING, SUCCESS, FAILED",
        max_length=16,
        default="PENDING",
    )
    target_type = models.CharField(
        help_text="Target model name",
        max_length=64,
        null=True,
        blank=True,
    )
    target_id = models.CharField(
        help_text="Target model ID",
        max_length=64,
        null=True,
        blank=True,
    )
    result = models.JSONField(
        help_text="Task result payload",
        null=True,
        blank=True,
    )
    error = models.TextField(
        help_text="Task error message",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        help_text="Create time of task", auto_now_add=True
    )
    updated_at = models.DateTimeField(
        help_text="Update time of task", auto_now=True
    )

    class Meta:
        app_label = "api"


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
    network = models.ForeignKey("Network", null=True, on_delete=models.DO_NOTHING)
    status = models.CharField(
        help_text="status of environment,can be CREATED|INITIALIZED|STARTED|ACTIVATED",
        max_length=32,
        default="CREATED",
    )
    firefly_status = models.CharField(
        help_text="status of firefly,can be NO|CHAINCODEINSTALLED|STARTED",
        max_length=32,
        default="NO",
    )
    Oracle_status = models.CharField(
        help_text="status of Oracle,can be NO|CHAINCODEINSTALLED",
        max_length=32,
        default="NO",
    )
    DMN_status = models.CharField(
        help_text="status of DMN,can be NO|CHAINCODEINSTALLED",
        max_length=32,
        default="NO",
    )
    create_at = models.DateTimeField(
        help_text="create time of environment", auto_now_add=True
    )

    class Meta:
        app_label = "api"


class EthEnvironment(models.Model):
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
    network = models.ForeignKey("Network", null=True, on_delete=models.DO_NOTHING)
    status = models.CharField(
        help_text="status of environment,can be CREATED|INITIALIZED|STARTED|ACTIVATED",
        max_length=32,
        default="CREATED",
    )
    firefly_status = models.CharField(
        help_text="status of firefly,can be NO|CHAINCODEINSTALLED|STARTED",
        max_length=32,
        default="NO",
    )
    Oracle_status = models.CharField(
        help_text="status of Oracle,can be NO|CHAINCODEINSTALLED",
        max_length=32,
        default="NO",
    )
    DMN_status = models.CharField(
        help_text="status of DMN,can be NO|CHAINCODEINSTALLED",
        max_length=32,
        default="NO",
    )
    identity_contract_status = models.CharField(
        help_text="status of identity contract,can be NO|PENDING|SETTINGUP|STARTED|FAILED",
        max_length=32,
        default="NO",
    )
    create_at = models.DateTimeField(
        help_text="create time of environment", auto_now_add=True
    )

    class Meta:
        app_label = "api"


__all__ = ["Task", "Environment", "EthEnvironment"]
