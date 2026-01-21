import logging

from rest_framework import serializers

from apps.core.models import UserProfile
from apps.fabric.models import FabricResourceSet
from common import ok

LOG = logging.getLogger(__name__)


class FabricResourceSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricResourceSet
        fields = ("id", "name")


class UserSerializer(serializers.ModelSerializer):
    organization = FabricResourceSetSerializer(allow_null=True)

    class Meta:
        model = UserProfile
        fields = ("id", "username", "role", "email", "organization")


def jwt_response_payload_handler(token, user=None, request=None):
    """
    Customize response for json web token

    :param token: the token value
    :param user: user object for UserProfile
    :param request: request context
    :return: UserSerializer data
    """
    return ok({
        "token": token,
        "user": UserSerializer(user, context={"request": request}).data,
    })
