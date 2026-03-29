"""Core domain models (stepwise migration, app_label pinned to api)."""

from django.contrib.auth.models import AbstractUser
from django.db import models

from common.enums import UserRole
from common.utils.common import make_uuid


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
        app_label = "api"

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


class LoleidoMembership(models.Model):
    id = models.UUIDField(
        primary_key=True,
        help_text="ID of LoleidoMembership",
        default=make_uuid,
        editable=False,
        unique=True,
    )
    loleido_organization = models.ForeignKey(
        "LoleidoOrganization",
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
        help_text="role of LoleidoMembership",
        default="Member",
        max_length=32,
        choices=(("Member", "Member"), ("Admin", "Admin"), ("Owner", "Owner")),
    )

    class Meta:
        unique_together = ("loleido_organization", "user")
        app_label = "api"


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
        through=LoleidoMembership,
        related_name="orgs",
    )

    class Meta:
        app_label = "api"


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

    class Meta:
        app_label = "api"


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

    class Meta:
        app_label = "api"


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

    class Meta:
        app_label = "api"


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

    class Meta:
        app_label = "api"


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
        "Environment",
        help_text="related environment_id",
        null=True,
        on_delete=models.SET_NULL,
    )
    last_active_consortium = models.ForeignKey(
        "Consortium",
        help_text="related consortium_id",
        null=True,
        on_delete=models.SET_NULL,
    )
    last_active_organization = models.ForeignKey(
        "ResourceSet",
        help_text="related middle_org_id",
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        app_label = "api"


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
        "Consortium",
        help_text="related consortium_id",
        null=True,
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        "LoleidoOrganization",
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
    chaincode = models.ForeignKey(
        "ChainCode",
        help_text="related chaincode_id",
        null=True,
        on_delete=models.CASCADE,
    )
    ethereum_contract = models.ForeignKey(
        "EthereumContract",
        help_text="related ethereum_contract_id",
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
    execution_layout = models.JSONField(
        help_text="execution layout metadata for BPMN runtime",
        null=True,
        blank=True,
        default=dict,
    )
    environment = models.ForeignKey(
        "Environment",
        help_text="related environment_id",
        null=True,
        on_delete=models.CASCADE,
    )
    eth_environment = models.ForeignKey(
        "EthEnvironment",
        help_text="related eth_environment_id",
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = "api"


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
    instance_chaincode_id = models.IntegerField(
        help_text="instance_id of BPMNInstance in chaincode",
        null=True,
        blank=True,
    )
    execution_bindings = models.JSONField(
        help_text="instance execution bindings such as participant accounts",
        null=True,
        blank=True,
        default=dict,
    )
    bpmn = models.ForeignKey(
        BPMN,
        help_text="related bpmn_id",
        null=False,
        on_delete=models.CASCADE,
    )
    create_at = models.DateTimeField(
        help_text="Create time of BPMNInstance", auto_now_add=True
    )
    update_at = models.DateTimeField(
        help_text="Update time of BPMNInstance", auto_now=True
    )

    class Meta:
        app_label = "api"


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

    class Meta:
        app_label = "api"


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
        "Consortium",
        help_text="related consortium_id",
        null=True,
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        "LoleidoOrganization",
        help_text="related organization_id",
        null=False,
        on_delete=models.CASCADE,
    )
    dmnContent = models.TextField(help_text="content of dmn file")
    svgContent = models.TextField(help_text="content of dmn`s svg file")
    fireflyDataId = models.CharField(
        help_text="FireFly data id for DMN content",
        max_length=255,
        null=True,
        blank=True,
    )
    cid = models.CharField(
        help_text="IPFS CID for DMN content",
        max_length=255,
        null=True,
        blank=True,
    )
    contentHash = models.CharField(
        help_text="keccak256 hash of DMN content",
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "api"


__all__ = [
    "UserProfile",
    "LoleidoMembership",
    "LoleidoOrganization",
    "Consortium",
    "Membership",
    "LoleidoOrgJoinConsortiumInvitation",
    "UserJoinOrgInvitation",
    "UserPreference",
    "BPMN",
    "BPMNInstance",
    "BpmnDmnBindingRecord",
    "DMN",
]
