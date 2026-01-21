#
# SPDX-License-Identifier: Apache-2.0
#
import logging

from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from common.serializers import PageQuerySerializer, ListResponseSerializer
from common.utils.common import random_name
from apps.infra.models import File, validate_file
from common.utils.common import to_form_paras

LOG = logging.getLogger(__name__)


class FileQuerySerializer(PageQuerySerializer, serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ("name", "type", "page", "per_page", "organization")


class FileIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ("id",)
        extra_kwargs = {"id": {"validators": [], "read_only": False}}


class FileInfoSerializer(serializers.ModelSerializer):
    url = serializers.URLField(help_text="File url for download")
    organization = serializers.UUIDField(
        required=True, read_only=False, help_text="Organization of file"
    )

    class Meta:
        model = File
        fields = ("id", "name", "type", "organization", "url", "created_at")
        extra_kwargs = {
            "id": {"validators": [], "read_only": False, "required": True},
            "name": {"required": True},
            "type": {"required": True},
            "url": {"required": True},
            "created_at": {"required": True},
        }


class FileListSerializer(ListResponseSerializer):
    data = FileInfoSerializer(many=True, help_text="Files list data")


class FileCreateSerializer(serializers.ModelSerializer):
    def to_form_paras(self):
        custom_paras = to_form_paras(self)

        return custom_paras

    class Meta:
        model = File
        fields = ("name", "type", "file")
        extra_kwargs = {
            "type": {"required": True},
            "file": {
                "required": True,
                "validators": [
                    FileExtensionValidator(allowed_extensions=["zip"]),
                    validate_file,
                ],
            },
        }

    def validate(self, attrs):
        file_type = attrs.get("type")
        name = attrs.get("name")

        if name is None:
            name = random_name(file_type)
            attrs["name"] = name

        return attrs
