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
from django.conf.urls.static import static

DEBUG = getattr(settings, "DEBUG")
API_VERSION = os.getenv("API_VERSION")
WEBROOT = os.getenv("WEBROOT", "api/v1")
API_PREFIX = WEBROOT.strip("/")

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

api_urlpatterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.environment.urls")),
    path("", include("apps.fabric.urls")),
    path("", include("apps.ethereum.urls")),
    path("", include("apps.infra.urls")),
]

urlpatterns = api_urlpatterns + [
    path("docs/", SchemaView.with_ui("swagger", cache_timeout=0), name="docs"),
    path("redoc/", SchemaView.with_ui("redoc", cache_timeout=0), name="redoc"),
]

if API_PREFIX:
    urlpatterns = [path(f"{API_PREFIX}/", include(urlpatterns))]

if DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
