# from rest_framework import viewsets, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from api.models import ConnectionRequest
# from .serializers import ConnectionRequestSerializer
# from api.models import Membership  # and MemUser if needed
# from api.controllers.protocols import didexchange, Controller

# class ConnectionManagerViewSet(viewsets.ViewSet):

#     def list(self, request, membership_id=None):
#         """
#         List established connections — mock, or integrate with Agent
#         """
#         # For now just return an empty list or later bind to actual ACA-py
#         return Response([])

#     @action(detail=False, methods=["get"], url_path=r"(?P<membership_id>[^/.]+)/connection_requests")
#     def pending_requests(self, request, membership_id=None):
#         """
#         List pending invitations TO this membership
#         """
#         invitations = ConnectionRequest.objects.filter(receiver_id=membership_id)
#         serializer = ConnectionRequestSerializer(invitations, many=True)
#         return Response(serializer.data)

#     def create(self, request):
#         """
#         发起连接请求，只记录
#         """
#         serializer = ConnectionRequestSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=["post"])
#     def accept(self, request, pk=None):
#         """
#         接收连接请求，调用 didexchange 逻辑建立 DID Connection
#         """
#         try:
#             conn_req = ConnectionRequest.objects.get(pk=pk)
#         except ConnectionRequest.DoesNotExist:
#             return Response({"error": "Invitation not found"}, status=404)

#         if conn_req.status == 'accepted':
#             return Response({"message": "Already accepted"}, status=400)

#         # 获取 Controller
#         sender_controller = self._get_controller(conn_req.sender_label, conn_req.sender_id)
#         receiver_controller = self._get_controller(conn_req.receiver_label, conn_req.receiver_id)

#         # 调用 ACA-py DID Exchange
#         try:
#             didexchange(sender_controller, receiver_controller)
#             conn_req.status = 'accepted'
#             conn_req.save()
#             return Response({"message": "Connection established"}, status=200)
#         except Exception as e:
#             return Response({"error": str(e)}, status=500)

#     def _get_controller(self, label, identifier):
#         """
#         从 Membership 或 MemUser 获取 controller 对象（url, public_did）
#         """
#         if label == "Membership":
#             from api.models import Membership
#             obj = Membership.objects.get(id=identifier)
#         else:  # "MemUser"
#             from api.models import MemUser
#             obj = MemUser.objects.get(id=identifier)

#         return Controller(url=obj.url, public_did=obj.public_did)