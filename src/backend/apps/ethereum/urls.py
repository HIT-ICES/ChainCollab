#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework.routers import DefaultRouter

from apps.ethereum.routes.ethereum.views import EthereumContractViewSet
from apps.ethereum.routes.ethereum_resource_set.views import EthereumResourceSetViewSet
from apps.ethereum.routes.ethereum_identity.views import EthereumIdentityViewSet

router = DefaultRouter(trailing_slash=False)

router.register(
    "eth-environments/(?P<environment_id>[^/.]+)/contracts",
    EthereumContractViewSet,
    basename="eth-ethereum-contract",
)
router.register(
    "ethereum_identities",
    EthereumIdentityViewSet,
    basename="ethereum_identity",
)
router.register(
    "eth-environments/(?P<environment_id>[^/.]+)/ethereum_identities",
    EthereumIdentityViewSet,
    basename="eth-ethereum-identity",
)
router.register(
    "resource_sets/(?P<resource_set_id>[^/.]+)/eth",
    EthereumResourceSetViewSet,
    basename="resource_set_eth",
)

urlpatterns = router.urls
