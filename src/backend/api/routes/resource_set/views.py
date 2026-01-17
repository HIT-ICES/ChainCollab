from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import ResourceSetSerializer

from api.models import (
    Environment,
    ResourceSet,
    Agent,
    Membership,
    FabricResourceSet,
    LoleidoOrganization,
)


class ResourceSetViewSet(viewsets.ViewSet):
    """
    ResourceSet管理
    """
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """
        获取ResourceSet列表
        """
        environment_id = request.parser_context["kwargs"].get("environment_id")
        queryset = ResourceSet.objects.filter(
            environment_id=environment_id
        )
        org_id = request.query_params.get("org_id",None)
        membership_id = request.query_params.get("membership_id", None)

        params = []

        if membership_id is not None:
            params.append(membership_id)
        elif org_id is not None:
            try:
                org = LoleidoOrganization.objects.get(pk=org_id)
            except LoleidoOrganization.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            memberships = Membership.objects.filter(loleido_organization=org)
            params = [membership.id for membership in memberships]
        else:
            serializer = ResourceSetSerializer(queryset, many=True)
            return Response(serializer.data)
        
        queryset = queryset.filter(membership_id__in=params)
        serializer = ResourceSetSerializer(queryset, many=True)
        return Response(serializer.data)
            




    def create(self, request, *args, **kwargs):
        """
        创建ResourceSet
        """
        environment_id = request.parser_context["kwargs"].get("environment_id")
        membership_id = request.data.get("membership_id")
        agent_id = request.data.get("agent_id")
        name = request.data.get("name")
        try:
            environment = Environment.objects.get(pk=environment_id)
        except Environment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            membership = Membership.objects.get(pk=membership_id)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        resource_set = ResourceSet.objects.create(
            environment=environment,
            membership=membership,
            name=name,
            agent=agent,
        )

        sub_resource_set = FabricResourceSet.objects.create(
            resource_set=resource_set,
            org_type=0,  # 0: user, 1: system
            name=resource_set.name,
        )

        serializer = ResourceSetSerializer(resource_set)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取ResourceSet详情
        """
        try:
            resource_set = ResourceSet.objects.get(pk=pk)
        except ResourceSet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ResourceSetSerializer(resource_set)
        return Response(serializer.data)

    def destroy(self, request, pk=None, *args, **kwargs):
        """
        删除ResourceSet
        """
        try:
            resource_set = ResourceSet.objects.get(pk=pk)
        except ResourceSet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        resource_set.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # def update(self, request, pk=None):
    #     """
    #     更新ResourceSet
    #     """
    #     try:
    #         resource_set = ResourceSet.objects.get(pk=pk)
    #     except ResourceSet.DoesNotExist:
    #         return Response(status=status.HTTP_404_NOT_FOUND)
    #     serializer = ResourceSetSerializer(resource_set, data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
