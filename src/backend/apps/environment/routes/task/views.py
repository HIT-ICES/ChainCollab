from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.environment.models import Task
from common import ok, err


class TaskViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _safe_limit(value, default: int = 20, max_limit: int = 200) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        if parsed < 1:
            return default
        return min(parsed, max_limit)

    def list(self, request, *args, **kwargs):
        target_type = request.query_params.get("target_type")
        target_id = request.query_params.get("target_id")
        limit = self._safe_limit(request.query_params.get("limit"))

        qs = Task.objects.all().order_by("-created_at")
        if target_type:
            qs = qs.filter(target_type=target_type)
        if target_id:
            qs = qs.filter(target_id=target_id)

        tasks = []
        for task in qs[:limit]:
            tasks.append(
                {
                    "id": str(task.id),
                    "type": task.type,
                    "status": task.status,
                    "step": task.step,
                    "target_type": task.target_type,
                    "target_id": task.target_id,
                    "result": task.result,
                    "error": task.error,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                }
            )
        return Response(ok(tasks), status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response(err("Task not found"), status=status.HTTP_404_NOT_FOUND)

        payload = {
            "id": str(task.id),
            "type": task.type,
            "status": task.status,
            "step": task.step,
            "target_type": task.target_type,
            "target_id": task.target_id,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
        return Response(ok(payload), status=status.HTTP_200_OK)
