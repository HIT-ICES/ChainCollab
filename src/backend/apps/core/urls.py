#
# SPDX-License-Identifier: Apache-2.0
#
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.routes.general.views import (
    RegisterViewSet,
    LoleidoTokenObtainPairView,
    LoleidoTokenVerifyView,
)
from apps.core.routes.user.views import UserViewSet
from apps.core.routes.search.views import SearchView
from apps.core.routes.loleido_organization.views import (
    LoleidoOrganizationViewSet,
    UserJoinOrgInviteViewSet,
)
from apps.core.routes.consortium.views import (
    ConsortiumViewSet,
    ConsortiumInviteViewSet,
)
from apps.core.routes.membership.views import MembershipViewSet
from apps.core.routes.bpmn.views import BPMNViewsSet, BPMNInstanceViewSet, DmnViewSet
from apps.core.routes.translator.views import TranslatorProxyViewSet

router = DefaultRouter(trailing_slash=False)

router.register("users", UserViewSet, basename="user")
router.register("register", RegisterViewSet, basename="register")
router.register("search", SearchView, basename="search")

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
    MembershipViewSet,
    basename="consortium-membership",
)
router.register(
    "consortiums/(?P<consortium_id>[^/.]+)/bpmns",
    BPMNViewsSet,
    basename="bpmn",
)
router.register(
    "bpmns/(?P<bpmn_id>[^/.]+)/bpmn-instances",
    BPMNInstanceViewSet,
    basename="bpmn-instance",
)
router.register(
    "consortiums/(?P<consortium_id>[^/.]+)/dmns",
    DmnViewSet,
    basename="dmn",
)
router.register("translator", TranslatorProxyViewSet, basename="translator")

urlpatterns = router.urls + [
    path("login", LoleidoTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token-verify", LoleidoTokenVerifyView.as_view(), name="token_verify"),
]
