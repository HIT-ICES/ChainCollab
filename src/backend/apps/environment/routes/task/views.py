from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.environment.models import Task
from common import ok, err


class TaskViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response(err("Task not found"), status=status.HTTP_404_NOT_FOUND)

        payload = {
            "id": str(task.id),
            "type": task.type,
            "status": task.status,
            "target_type": task.target_type,
            "target_id": task.target_id,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
        return Response(ok(payload), status=status.HTTP_200_OK)
