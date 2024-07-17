#
# SPDX-License-Identifier: Apache-2.0
#
"""api_engine URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.conf import settings
from django.urls import path, include
from rest_framework import permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from django.conf.urls.static import static

from api.routes.network.views import NetworkViewSet
from api.routes.agent.views import AgentViewSet
from api.routes.node.views import NodeViewSet
from api.routes.fabric_resource_set.views import FabricResourceSetViewSet
from api.routes.user.views import UserViewSet
from api.routes.file.views import FileViewSet
from api.routes.general.views import RegisterViewSet
from api.routes.channel.views import ChannelViewSet
from api.routes.chaincode.views import ChainCodeViewSet
from api.routes.ca.views import FabricCAViewSet
from api.routes.firefly.views import FireflyViewSet
from api.routes.general.views import (
    LoleidoTokenObtainPairView,
    LoleidoTokenVerifyView,
)
from api.routes.loleido_organization.views import (
    LoleidoOrganizationViewSet,
    UserJoinOrgInviteViewSet,
)
from api.routes.consortium.views import ConsortiumViewSet, ConsortiumInviteViewSet
from api.routes.memebership.views import MemebershipViewSet
from api.routes.environment.views import EnvironmentViewSet, EnvironmentOperateViewSet
from api.routes.resource_set.views import ResourceSetViewSet
from api.routes.bpmn.views import (
    BPMNViewsSet,
    BPMNInstanceViewSet,
    BPMNBindingRecordViewSet,
    DmnViewSet,
)
from api.routes.fabric_identity.views import FabricIdentityViewSet
from api.routes.api_secret_key.views import APISecretKeyViewSet

DEBUG = getattr(settings, "DEBUG")
API_VERSION = os.getenv("API_VERSION")
WEBROOT = os.getenv("WEBROOT")
# WEBROOT = "/".join(WEBROOT.split("/")[1:]) + "/"
WEBROOT = "api/v1/"

swagger_info = openapi.Info(
    title="Cello API Engine Service",
    default_version="1.0",
    description="""
    This is swagger docs for Cello API engine.
    """,
)

SchemaView = get_schema_view(
    validators=["ssv", "flex"],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# define and register routers of api
router = DefaultRouter(trailing_slash=False)

router.register("users", UserViewSet, basename="user")
router.register("files", FileViewSet, basename="file")
router.register("register", RegisterViewSet, basename="register")

router.register("agents", AgentViewSet, basename="agent")  # No Change

router.register("api_secret_keys", APISecretKeyViewSet, basename="api_secret_key")
router.register("fabric_identities/", FabricIdentityViewSet, basename="fabric_identity")

router.register(
    "fabric_resource_sets", FabricResourceSetViewSet, basename="fabric_resource_set"
)  # Need to Expose?

router.register(
    "resource_sets/(?P<resource_set_id>[^/.]+)/nodes",
    NodeViewSet,
    basename="resource_set_node",
)
router.register(
    "resource_sets/(?P<resource_set_id>[^/.]+)/cas",
    FabricCAViewSet,
    basename="resource_set_ca",
)
router.register(
    "environments/(?P<environment_id>[^/.]+)/channels",
    ChannelViewSet,
    basename="environment-channel",
)
router.register(
    "environments/(?P<environment_id>[^/.]+)/networks",
    NetworkViewSet,
    basename="network",
)

# belong to consortium?environment
router.register(
    "environments/(?P<environment_id>[^/.]+)/chaincodes",
    ChainCodeViewSet,
    basename="chaincode",
)
router.register(
    "environments/(?P<environment_id>[^/.]+)/fireflys",
    FireflyViewSet,
    basename="firefly",
)
# TODO MODIFY URL FOR FIREFLY
# router.register("fireflys", FireflyViewSet, basename="firefly")
router.register(
    "consortiums/(?P<consortium_id>[^/.]+)/bpmns", BPMNViewsSet, basename="bpmn"
)
router.register(
    "bpmns/(?P<bpmn_id>[^/.]+)/bpmn-instances",
    BPMNInstanceViewSet,
    basename="bpmn-instance",
)

router.register(
    "bpmn-instances/(?P<bpmn_instance_id>[^/.]+)/binding-records",
    BPMNBindingRecordViewSet,
    basename="bpmn-binding-record",
)
router.register(
    "consortiums/(?P<consortium_id>[^/.]+)/dmns", DmnViewSet, basename="dmn"
)

router.register("organizations", LoleidoOrganizationViewSet, basename="organization")
router.register(
    "organization-invites", UserJoinOrgInviteViewSet, basename="organization-invite"
)
router.register("consortiums", ConsortiumViewSet, basename="consortium")
router.register(
    "consortium-invites", ConsortiumInviteViewSet, basename="consortium-invite"
)
router.register(
    "consortium/(?P<consortium_id>[^/.]+)/memberships",
    MemebershipViewSet,
    basename="consortium-membership",
)
router.register(
    "consortium/(?P<consortium_id>[^/.]+)/environments",
    EnvironmentViewSet,
    basename="consortium-environment",
)
router.register(
    "environments", EnvironmentOperateViewSet, basename="environment-operate"
)
router.register(
    "environments/(?P<environment_id>[^/.]+)/resource_sets",
    ResourceSetViewSet,
    basename="environment-resource_set",
)
urlpatterns = router.urls

urlpatterns += [
    path("login", LoleidoTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token-verify", LoleidoTokenVerifyView.as_view(), name="token_verify"),
    path("docs/", SchemaView.with_ui("swagger", cache_timeout=0), name="docs"),
    path("redoc/", SchemaView.with_ui("redoc", cache_timeout=0), name="redoc"),
]

if DEBUG:
    urlpatterns = [path(WEBROOT, include(urlpatterns))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
