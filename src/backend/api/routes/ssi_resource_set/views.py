from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from api.models import SSIResourceSet, Environment, Membership, LoleidoOrganization,Consortium, SSIAgentNode
from .serializers import SSIResourceSetSerializer


class SSIResourceSetViewSet(viewsets.ViewSet):
    """
    SSIResourceSet 管理
    """

    def list(self, request, *args, **kwargs):
        """
        获取 SSIResourceSet 列表，可通过 consortium_id 和 membership_id 过滤
        """
        consortium_id = request.parser_context["kwargs"].get("consortium_id")
        membership_id = request.query_params.get("membership_id")

        queryset = SSIResourceSet.objects.filter(consortium_id=consortium_id)
        if membership_id:
            queryset = queryset.filter(membership_id=membership_id)

        serializer = SSIResourceSetSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        创建 SSIResourceSet
        """
        consortium_id = request.parser_context["kwargs"].get("consortium_id")
        membership_id = request.data.get("membership_id")
        # 当前 Membership name
        name = request.data.get("name", "")
        SSI_agent_external = request.data.get("SSI_agent_external", False)

        try:
            consortium = Consortium.objects.get(pk=consortium_id)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            membership = Membership.objects.get(pk=membership_id)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ssi_resource_set = SSIResourceSet.objects.create(
            consortium=consortium,
            membership=membership,
            name=name,
            SSI_agent_external=SSI_agent_external,
        )

        serializer = SSIResourceSetSerializer(ssi_resource_set)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取单个 SSIResourceSet 详情
        """
        try:
            ssi_resource_set = SSIResourceSet.objects.get(pk=pk)
        except SSIResourceSet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = SSIResourceSetSerializer(ssi_resource_set)
        return Response(serializer.data)

    def destroy(self, request, pk=None, *args, **kwargs):
        """
        删除 SSIResourceSet
        """
        try:
            ssi_resource_set = SSIResourceSet.objects.get(pk=pk)
        except SSIResourceSet.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ssi_resource_set.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
