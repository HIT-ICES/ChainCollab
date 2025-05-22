from rest_framework import viewsets, status
from rest_framework.response import Response

from api.models import Consortium
from rest_framework.decorators import action

from .serializers import (
    ConsortiumSerializer,
    LoliedoOrgJoinConsortiumInvitionSerializer,
)
from api.models import (
    LoleidoOrganization,
    LoleidoOrgJoinConsortiumInvitation,
    Membership,
    Environment,
)


class ConsortiumViewSet(viewsets.ViewSet):
    """
    联盟管理
    """

    def list(self, request):
        """
        获取联盟列表
        """
        org_uuid = request.query_params.get("org_uuid", None)
        orgs = []
        if org_uuid:
            org = LoleidoOrganization.objects.get(id=org_uuid)
            orgs = [org] if org.members.filter(id=request.user.id).exists() else []
        else:
            user = request.user
            orgs = user.orgs.all()
        queryset = Consortium.objects.filter(orgs__in=orgs).distinct()
        serializer = ConsortiumSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """
        创建联盟
        """
        name = request.data.get("name")
        baseOrgId = request.data.get("baseOrgId")
        createSSI = request.data.get("createSSI", False)
        user = request.user
        try:
            consortium = Consortium.objects.create(name=name)
            # create a Memebership for the baseOrg in the consortium
            baseOrg = LoleidoOrganization.objects.get(id=baseOrgId)
            if createSSI:
                ssi_membership = Membership.objects.create(
                    loleido_organization=baseOrg,
                    consortium=consortium,
                    name=f"{baseOrg.name}-{consortium.name}-SSI",
                    primary_contact_email=user.email,
                    membership_type='ssi',
                )
            else:
                membership = Membership.objects.create(
                loleido_organization=baseOrg,
                consortium=consortium,
                name=baseOrg.name + "-" + consortium.name,
                primary_contact_email=user.email,
                membership_type='standard',
                )
        except Exception as e:
            return Response(
                data={"message": e.args}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = ConsortiumSerializer(consortium)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """
        获取联盟详情
        """
        try:
            consortium = Consortium.objects.get(pk=pk)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ConsortiumSerializer(consortium)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """
        更新联盟
        """
        try:
            consortium = Consortium.objects.get(pk=pk)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ConsortiumSerializer(consortium, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """
        更新联盟
        """
        try:
            consortium = Consortium.objects.get(pk=pk)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ConsortiumSerializer(consortium, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """
        删除联盟
        """
        try:
            consortium = Consortium.objects.get(pk=pk)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        consortium.delete()
        # Remove all the membership of the consortium
        Membership.objects.filter(consortium=consortium).delete()
        # Remove all the invitions of the consortium
        LoleidoOrgJoinConsortiumInvitation.objects.filter(
            consortium=consortium
        ).delete()
        # Remove all the environments of the consortium
        Environment.objects.filter(consortium=consortium).delete()
        return Response(
            {"message": "Delete Success"}, status=status.HTTP_204_NO_CONTENT
        )


class ConsortiumInviteViewSet(viewsets.ViewSet):
    """
    联盟邀请管理
    """

    def create(self, request):
        """
        邀请特定组织加入联盟
        """
        org_uuid = request.data.get("org_uuid")
        consortium_uuid = request.data.get("consortium_uuid")
        invitor_uuid = request.data.get("invitor_uuid")
        try:
            loleido_org = LoleidoOrganization.objects.get(id=org_uuid)
        except LoleidoOrganization.DoesNotExist:
            return Response(
                {"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"message": e.args}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consortium = Consortium.objects.get(pk=consortium_uuid)
        except Consortium.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            invitor = LoleidoOrganization.objects.get(id=invitor_uuid)
        except LoleidoOrganization.DoesNotExist:
            return Response(
                {"message": "Invitor not found"}, status=status.HTTP_404_NOT_FOUND
            )

        invition = LoleidoOrgJoinConsortiumInvitation.objects.create(
            loleido_organization=loleido_org,
            consortium=consortium,
            invitor=invitor,
        )
        invition.save()
        return Response(data={"message": "Success"}, status=status.HTTP_201_CREATED)

    def list(self, request):
        """
        组织获取联盟邀请列表
        """
        org_uuid = request.query_params.get("org_uuid")
        try:
            loleido_org = LoleidoOrganization.objects.get(id=org_uuid)
        except LoleidoOrganization.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        queryset = LoleidoOrgJoinConsortiumInvitation.objects.filter(
            loleido_organization=loleido_org
        )
        serializer = LoliedoOrgJoinConsortiumInvitionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """
        获取联盟邀请详情
        """
        try:
            invition = LoleidoOrgJoinConsortiumInvitation.objects.get(pk=pk)
        except LoleidoOrgJoinConsortiumInvitation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        organizations_of_user = request.user.orgs.all()
        if invition.loleido_organization not in organizations_of_user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = LoliedoOrgJoinConsortiumInvitionSerializer(invition)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        """
        更新联盟邀请
        """
        try:
            invition = LoleidoOrgJoinConsortiumInvitation.objects.get(pk=pk)
        except LoleidoOrgJoinConsortiumInvitation.DoesNotExist:
            return Response({"message": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        organizations_of_user = request.user.orgs.all()
        if invition.loleido_organization not in organizations_of_user:
            return Response(
                {"message": "You are not the owner of the invition"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if invition.status == "accept" or invition.status == "reject":
            return Response(
                {"message": "Invition has been processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.data.get("status") not in ["accept", "reject"]:
            return Response(
                {"message": "status should be accept or reject"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invition.status = request.data.get("status")
        invition.save()
        if invition.status == "accept":
            # create a Memebership for the org in the consortium
            membership = Membership.objects.create(
                loleido_organization=invition.loleido_organization,
                consortium=invition.consortium,
                name=invition.loleido_organization.name
                + "-"
                + invition.consortium.name,
            )
            membership.save()
            return Response(data={"message": "Accept"}, status=status.HTTP_200_OK)
        return Response(data={"message": "Reject"}, status=status.HTTP_200_OK)
