#
# SPDX-License-Identifier: Apache-2.0
#
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.enums import HostType
from common.exceptions import (
    ResourceNotFound,
    ResourceExists,
    CustomError,
    NoResource,
    ResourceInUse,
)
from apps.infra.models import Agent, KubernetesConfig
from apps.core.models import LoleidoOrganization
from apps.infra.routes.agent.serializers import (
    AgentQuery,
    AgentListResponse,
    AgentCreateBody,
    AgentIDSerializer,
    AgentPatchBody,
    AgentUpdateBody,
    AgentInfoSerializer,
    AgentApplySerializer,

    AgentSerializer,
)
from common.utils.common import with_common_response
from common import ok, err

LOG = logging.getLogger(__name__)


class AgentViewSet(viewsets.ViewSet):
    """Class represents agent related operations."""

    permission_classes = [
        IsAuthenticated,
    ]

    @swagger_auto_schema(
        query_serializer=AgentQuery,
        responses=with_common_response(
            with_common_response({status.HTTP_200_OK: AgentListResponse})
        ),
    )
    def list(self, request):
        """
        List Agents

        :param request: query parameter
        :return: agent list
        :rtype: list
        """

        public_agents = Agent.objects.filter(organization__isnull=True)

        organization_id = request.query_params.get("organization_id", None)
        if organization_id is None:
            return Response(
                public_agents.all(), status=status.HTTP_200_OK
            )
        
        try:
            organization = LoleidoOrganization.objects.get(id=organization_id)
        except LoleidoOrganization.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        org_agents = Agent.objects.filter(organization=organization)
        
        agent_list = list(org_agents) + list(public_agents)

        return Response(data={
            "data": [AgentSerializer(agent).data for agent in agent_list]
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AgentCreateBody,
        responses=with_common_response({status.HTTP_201_CREATED: AgentIDSerializer}),
    )
    def create(self, request):
        name = request.data.get("name")
        agent_type = request.data.get("type", "Docker")
        urls = request.data.get("urls")
        config_file = request.data.get("config_file", None)
        org_id = request.data.get("organization_id", None)

        if org_id:
            try:
                organization = LoleidoOrganization.objects.get(id=org_id)
            except LoleidoOrganization.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
        
        agent = Agent.objects.create(
            name=name,
            type=agent_type,
            urls=urls,
            config_file=config_file,
            organization=organization,
        )
        serializer = AgentSerializer(agent)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses=with_common_response({status.HTTP_200_OK: AgentInfoSerializer})
    )
    def retrieve(self, request, pk=None):
        """
        Retrieve agent

        :param request: destory parameter
        :param pk: primary key
        :return: none
        :rtype: rest_framework.status
        """
        try:
            agent = Agent.objects.get(id=pk)
            serializer = AgentSerializer(agent)
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        request_body=AgentUpdateBody,
        responses=with_common_response({status.HTTP_202_ACCEPTED: "Accepted"}),
    )
    def update(self, request, pk=None):
        """
        Update Agent

        Update special agent with id.
        """
        try:
            serializer = AgentUpdateBody(data=request.data)
            if serializer.is_valid(raise_exception=True):
                name = serializer.validated_data.get("name")
                # urls = serializer.validated_data.get("urls")
                # organization = request.user.organization
                try:
                    if Agent.objects.get(name=name):
                        raise ResourceExists
                except ObjectDoesNotExist:
                    pass
                Agent.objects.filter(id=pk).update(name=name)

                return Response(ok(None), status=status.HTTP_202_ACCEPTED)
        except ResourceExists as e:
            raise e
        except Exception as e:
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        request_body=AgentPatchBody,
        responses=with_common_response({status.HTTP_202_ACCEPTED: "Accepted"}),
    )
    def partial_update(self, request, pk=None):
        """
        Partial Update Agent

        Partial update special agent with id.
        """
        try:
            serializer = AgentPatchBody(data=request.data)
            if serializer.is_valid(raise_exception=True):
                name = serializer.validated_data.get("name")
                capacity = serializer.validated_data.get("capacity")
                log_level = serializer.validated_data.get("log_level")
                try:
                    agent = Agent.objects.get(id=pk)
                except ObjectDoesNotExist:
                    raise ResourceNotFound
                else:
                    if name:
                        agent.name = name
                    if capacity:
                        agent.capacity = capacity
                    if log_level:
                        agent.log_level = log_level
                    agent.save()

                    return Response(ok(None), status=status.HTTP_202_ACCEPTED)
        except ResourceNotFound as e:
            raise e
        except Exception as e:
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses=with_common_response(
            {
                status.HTTP_204_NO_CONTENT: "No Content",
                status.HTTP_404_NOT_FOUND: "Not Found",
            }
        )
    )
    def destroy(self, request, pk=None):
        """
        Delete agent

        :param request: destory parameter
        :param pk: primary key
        :return: none
        :rtype: rest_framework.status
        """
        try:
            agent = Agent.objects.get(id=pk)
            agent.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        method="post",
        request_body=AgentApplySerializer,
        responses=with_common_response({status.HTTP_200_OK: AgentIDSerializer}),
    )
    @action(methods=["post"], detail=False, url_path="organization")
    def apply(self, request):
        """
        Apply Agent

        Apply Agent
        """
        try:
            serializer = AgentApplySerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                agent_type = serializer.validated_data.get("type")
                capacity = serializer.validated_data.get("capacity")

                if request.user.organization is None:
                    raise CustomError(detail="Need join in organization")
                agent_count = Agent.objects.filter(
                    organization=request.user.organization
                ).count()
                if agent_count > 0:
                    raise CustomError(detail="Already applied agent.")

                agents = Agent.objects.filter(
                    organization__isnull=True,
                    type=agent_type,
                    capacity__gte=capacity,
                    schedulable=True,
                ).order_by("capacity")
                if len(agents) == 0:
                    raise NoResource

                agent = agents[0]
                agent.organization = request.user.organization
                agent.save()

                response = AgentIDSerializer(data=agent.__dict__)
                if response.is_valid(raise_exception=True):
                    return Response(
                        ok(response.validated_data), status=status.HTTP_200_OK
                    )
        except NoResource as e:
            raise e
        except Exception as e:
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        method="delete",
        responses=with_common_response({status.HTTP_204_NO_CONTENT: "No Content"}),
    )
    @action(methods=["delete"], detail=True, url_path="organization")
    def release(self, request, pk=None):
        """
        Release Agent

        Release Agent
        """
        try:
            try:
                if request.user.is_operator:
                    agent = Agent.objects.get(id=pk)
                else:
                    if request.user.organization is None:
                        raise CustomError("Need join in organization")
                    agent = Agent.objects.get(
                        id=pk, organization=request.user.organization
                    )
            except ObjectDoesNotExist:
                raise ResourceNotFound
            else:
                agent.organization = None
                agent.save()

                return Response(ok(None), status=status.HTTP_204_NO_CONTENT)
        except ResourceNotFound as e:
            raise e
        except Exception as e:
            return Response(err(e.args), status=status.HTTP_400_BAD_REQUEST)
