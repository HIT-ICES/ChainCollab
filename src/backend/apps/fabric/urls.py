#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework.routers import DefaultRouter

from apps.fabric.routes.network.views import NetworkViewSet
from apps.fabric.routes.node.views import NodeViewSet
from apps.fabric.routes.fabric_resource_set.views import FabricResourceSetViewSet
from apps.fabric.routes.channel.views import ChannelViewSet
from apps.fabric.routes.chaincode.views import ChainCodeViewSet
from apps.fabric.routes.ca.views import FabricCAViewSet
from apps.fabric.routes.fabric_identity.views import FabricIdentityViewSet

router = DefaultRouter(trailing_slash=False)

router.register("fabric_resource_sets", FabricResourceSetViewSet, basename="fabric_resource_set")
router.register("fabric_identities", FabricIdentityViewSet, basename="fabric_identity")

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
router.register(
    "environments/(?P<environment_id>[^/.]+)/chaincodes",
    ChainCodeViewSet,
    basename="chaincode",
)

urlpatterns = router.urls
