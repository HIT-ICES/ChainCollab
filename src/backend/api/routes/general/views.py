#
# SPDX-License-Identifier: Apache-2.0
#

from .serializers import (
    LoginBody,
    LoginSuccessBody,
    TokenVerifyRequest,
)
from api.config import CELLO_HOME
from api.common import ok, err
from api.utils import zip_dir
from api.utils.common import random_name

from api.routes.general.serializers import (
    RegisterBody,
    RegisterResponse,
)
from api.models import (
    UserProfile,
    LoleidoOrganization,
    Consortium,
    Environment,
    Membership,
)
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import logging
import base64

from django.contrib.auth import authenticate
from rest_framework import viewsets, status
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenVerifyView,
)
from rest_framework_simplejwt.tokens import (
    RefreshToken,
    AccessToken,
)
from rest_framework_simplejwt.exceptions import TokenError
from django.db import transaction

LOG = logging.getLogger(__name__)


class RegisterViewSet(viewsets.ViewSet):
    @transaction.atomic
    def create(self, request):
        """
        Register a new user and organization with it or not
        """
        try:
            serializer = RegisterBody(data=request.data)
            if serializer.is_valid(raise_exception=True):
                email = serializer.validated_data.get("email")
                # orgname = serializer.validated_data.get("orgName")
                password = serializer.validated_data.get("password")
                username = serializer.validated_data.get("username")

                try:
                    UserProfile.objects.get(email=email)
                except ObjectDoesNotExist:
                    pass
                except MultipleObjectsReturned:
                    return Response(
                        err("Email Aleady exists!"), status=status.HTTP_409_CONFLICT
                    )
                else:
                    return Response(
                        err("Email Aleady exists!"), status=status.HTTP_409_CONFLICT
                    )

                # Creating a Loleido User
                user = UserProfile.objects.create_user(
                    email=email,
                    username=username,
                )
                user.set_password(password)
                user.save()

                response = RegisterResponse(
                    data={
                        "status": "Success",
                    }
                )
                if response.is_valid(raise_exception=True):
                    return Response(
                        data=ok(response.validated_data), status=status.HTTP_200_OK
                    )
        except Exception as e:
            print(e)
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    def _conversion_msp_tls(self, name):
        """
        msp and tls from zip file to byte

        :param name: organization name
        :return: msp, tls
        :rtype: bytes
        """
        try:
            dir_org = "{}/{}/crypto-config/peerOrganizations/{}/".format(
                CELLO_HOME, name, name
            )

            zip_dir("{}msp".format(dir_org), "{}msp.zip".format(dir_org))
            with open("{}msp.zip".format(dir_org), "rb") as f_msp:
                msp = base64.b64encode(f_msp.read())

            zip_dir("{}tlsca".format(dir_org), "{}tls.zip".format(dir_org))
            with open("{}tls.zip".format(dir_org), "rb") as f_tls:
                tls = base64.b64encode(f_tls.read())
        except Exception as e:
            raise e

        return msp, tls


class LoleidoTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = LoginBody(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = authenticate(
                request,
                username=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
            if user is not None:
                print(user)
                print("LOGIN")
                refresh = RefreshToken.for_user(user)
                data = {
                    "token": str(refresh.access_token),
                    "user": user,
                }
                response = LoginSuccessBody(instance=data)
                return Response(
                    data=ok(response.data),
                    status=200,
                )
        return super().post(request, *args, **kwargs)


class LoleidoTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        serializer = TokenVerifyRequest(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                access_token = AccessToken(
                    token=serializer.validated_data["token"],
                )
                user = UserProfile.objects.get(pk=access_token["user_id"])
                if user is not None:
                    data = {
                        "token": str(access_token.token),
                        "user": user,
                    }
                    response = LoginSuccessBody(instance=data)
                    return Response(
                        data=ok(response.data),
                        status=200,
                    )
            except TokenError:
                LOG.warn("invalid token error")
                return Response(data=err(msg="invalid token"), status=401)

        return super().post(request, *args, **kwargs)
