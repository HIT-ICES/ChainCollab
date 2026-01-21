#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework.routers import DefaultRouter

from apps.infra.routes.agent.views import AgentViewSet
from apps.infra.routes.file.views import FileViewSet
from apps.infra.routes.api_secret_key.views import APISecretKeyViewSet
from apps.infra.routes.firefly.views import FireflyViewSet

router = DefaultRouter(trailing_slash=False)

router.register("agents", AgentViewSet, basename="agent")
router.register("files", FileViewSet, basename="file")
router.register("api_secret_keys", APISecretKeyViewSet, basename="api_secret_key")
router.register(
    "environments/(?P<environment_id>[^/.]+)/fireflys",
    FireflyViewSet,
    basename="firefly",
)
router.register(
    "eth-environments/(?P<environment_id>[^/.]+)/fireflys",
    FireflyViewSet,
    basename="eth-firefly",
)

urlpatterns = router.urls
