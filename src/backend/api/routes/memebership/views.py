from rest_framework import viewsets, status
from rest_framework.response import Response

from .serializers import MembershipSerializer

from api.models import LoleidoOrganization, Consortium, Membership


class MemebershipViewSet(viewsets.ViewSet):
    """
    Membership管理
    """

    def list(self, request, *args, **kwargs):
        """
        获取Membership列表
        """
        consortium_id = kwargs.get("consortium_id")
        org_id = request.data.get("org_uuid", None)

        try:
            consortium = Consortium.objects.get(pk=consortium_id)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not org_id:
            # return all but filter org for system
            filtered_memberships = Membership.objects.exclude(name__contains="system")
            queryset = filtered_memberships.filter(consortium=consortium)
            serializer = MembershipSerializer(queryset, many=True)
            return Response(serializer.data)

        try:
            loleido_org = LoleidoOrganization.objects.get(id=org_id)
        except LoleidoOrganization.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        queryset = Membership.objects.filter(
            consortium=consortium, loleido_org=loleido_org
        )
        serializer = MembershipSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        创建Membership
        """
        consortium_id = kwargs.get("consortium_id")
        org_id = request.data.get("org_uuid", None)
        name = request.data.get("name")
        email = request.data.get("primary_contact_email", "org.example.com")
        try:
            consortium = Consortium.objects.get(pk=consortium_id)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            loleido_org = LoleidoOrganization.objects.get(id=org_id)
        except LoleidoOrganization.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        membership = Membership.objects.create(
            loleido_organization=loleido_org,
            consortium=consortium,
            name=name,
            primary_contact_email=email,
        )
        membership.save()
        serializer = MembershipSerializer(membership)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        获取Membership详情
        """
        try:
            membership = Membership.objects.get(pk=pk)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = MembershipSerializer(membership)
        return Response(serializer.data)

    # def update(self, request, pk=None):
    #     """
    #     更新Membership
    #     """
    #     consortium_id = request.kwargs.get("consortium_id")
    #     try:
    #         consortium = Consortium.objects.get(pk=consortium_id)
    #     except Consortium.DoesNotExist:
    #         return Response(status=status.HTTP_404_NOT_FOUND)

    #     try:
    #         membership = Membership.objects.get(pk=pk, consortium=consortium)
    #     except Membership.DoesNotExist:
    #         return Response(status=status.HTTP_404_NOT_FOUND)
    #     serializer = MembershipSerializer(membership, data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None, *args, **kwargs):
        """
        删除Membership
        """
        consortium_id = kwargs.get("consortium_id")
        try:
            consortium = Consortium.objects.get(pk=consortium_id)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            membership = Membership.objects.get(pk=pk, consortium=consortium)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        membership.delete()
        return Response(
            {"message": "Membership with id `{}` has been deleted.".format(pk)},
            status=status.HTTP_204_NO_CONTENT,
        )
