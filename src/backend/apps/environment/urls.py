#
# SPDX-License-Identifier: Apache-2.0
#
from rest_framework.routers import DefaultRouter

from apps.environment.routes.environment.views import (
    EnvironmentViewSet,
    EnvironmentOperateViewSet,
    EthEnvironmentViewSet,
    EthEnvironmentOperateViewSet,
)
from apps.environment.routes.chainlink_job.views import ChainlinkJobViewSet
from apps.environment.routes.resource_set.views import ResourceSetViewSet
from apps.environment.routes.task.views import TaskViewSet

router = DefaultRouter(trailing_slash=False)

router.register("tasks", TaskViewSet, basename="task")
router.register(
    "consortium/(?P<consortium_id>[^/.]+)/environments",
    EnvironmentViewSet,
    basename="consortium-environment",
)
router.register("environments", EnvironmentOperateViewSet, basename="environment-operate")
router.register(
    "consortium/(?P<consortium_id>[^/.]+)/eth-environments",
    EthEnvironmentViewSet,
    basename="eth-environment",
)
router.register(
    "eth-environments",
    EthEnvironmentOperateViewSet,
    basename="eth-environment-operate",
)
router.register(
    "eth-environments/(?P<environment_id>[^/.]+)/chainlink-jobs",
    ChainlinkJobViewSet,
    basename="eth-environment-chainlink-jobs",
)
router.register(
    "environments/(?P<environment_id>[^/.]+)/resource_sets",
    ResourceSetViewSet,
    basename="environment-resource_set",
)

urlpatterns = router.urls
