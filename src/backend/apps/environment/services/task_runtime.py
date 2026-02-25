from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from threading import Thread
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.environment.models import Task

LOG = logging.getLogger("api")


def _runtime_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "src":
            runtime = parent / "runtime" / "tasks"
            runtime.mkdir(parents=True, exist_ok=True)
            return runtime
    runtime = Path("/tmp") / "runtime" / "tasks"
    runtime.mkdir(parents=True, exist_ok=True)
    return runtime


def _task_log_path(task_id: str) -> Path:
    return _runtime_dir() / f"task-{task_id}.log"


def _append_task_log(path: Path, message: str):
    timestamp = timezone.now().isoformat()
    with path.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _read_task_log_tail(path: Path, limit: int = 20000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    if len(data) <= limit:
        return data
    return data[-limit:]


def _stream_process_output(process: subprocess.Popen, log_path: Path | None):
    if not process.stdout:
        return
    for line in process.stdout:
        line = line.rstrip()
        if log_path and line:
            _append_task_log(log_path, line)


def _ensure_idempotent_task_request(
    request,
    env_id: str,
    task_type: str,
    mode: str | None = None,
):
    force = bool(request.data.get("force"))
    base_key = request.data.get("idempotency_key") or f"{task_type}:{env_id}"
    if mode:
        base_key = f"{base_key}:{mode}"
    idempotency_key = f"{base_key}:{uuid4()}" if force else base_key

    existing = (
        Task.objects.filter(idempotency_key=idempotency_key)
        .order_by("-created_at")
        .first()
    )
    if existing:
        if existing.status in ["PENDING", "RUNNING"]:
            return {
                "response": Response(
                    {"message": "Task is running", "task_id": str(existing.id)},
                    status=status.HTTP_202_ACCEPTED,
                )
            }
        if existing.status == "SUCCESS":
            return {
                "response": Response(
                    {"message": "Task already completed", "result": existing.result},
                    status=status.HTTP_200_OK,
                )
            }
        if existing.status == "FAILED" and not force:
            return {
                "response": Response(
                    {
                        "message": "Task failed previously, use force to retry",
                        "task_id": str(existing.id),
                        "error": existing.error,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            }

    return {"idempotency_key": idempotency_key, "force": force}


def create_task(
    *,
    task_type: str,
    target_type: str,
    target_id: str,
    idempotency_key: str,
    status_value: str = "PENDING",
    rollback_info: dict | None = None,
) -> Task:
    with transaction.atomic():
        return Task.objects.create(
            type=task_type,
            target_type=target_type,
            target_id=target_id,
            status=status_value,
            idempotency_key=idempotency_key,
            rollback_info=rollback_info or {},
        )


def create_task_with_status_transition(
    *,
    task_type: str,
    target_type: str,
    target_id: str,
    idempotency_key: str,
    target_obj,
    status_field: str,
    pending_value: str = "PENDING",
    extra_rollback: dict | None = None,
) -> tuple[Task, str]:
    with transaction.atomic():
        previous_status = getattr(target_obj, status_field)
        setattr(target_obj, status_field, pending_value)
        target_obj.save(update_fields=[status_field])
        rollback_info = {status_field: previous_status}
        if extra_rollback:
            rollback_info.update(extra_rollback)
        task = Task.objects.create(
            type=task_type,
            target_type=target_type,
            target_id=target_id,
            status="PENDING",
            idempotency_key=idempotency_key,
            rollback_info=rollback_info,
        )
    return task, previous_status


def _start_task_async(
    task: Task,
    handler,
    *args,
    rollback_model=None,
    rollback_target_type: str | None = None,
    **kwargs,
):
    def runner():
        log_path = _task_log_path(str(task.id))
        _append_task_log(
            log_path, f"task start type={task.type} target={task.target_type}:{task.target_id}"
        )
        task.status = "RUNNING"
        task.step = "RUNNING"
        task.result = (task.result or {})
        if isinstance(task.result, dict):
            task.result.setdefault("log_path", str(log_path))
        else:
            task.result = {"log_path": str(log_path)}
        task.save(update_fields=["status", "step", "result", "updated_at"])
        LOG.info("Task %s started (%s)", task.id, task.type)
        try:
            result = handler(*args, **kwargs)
            _append_task_log(log_path, "task handler finished")
            task.status = "SUCCESS"
            task.step = "SUCCESS"
            if isinstance(result, dict):
                result.setdefault("log_path", str(log_path))
                task.result = result
            else:
                task.result = {"result": result, "log_path": str(log_path)}
            task.error = None
            LOG.info("Task %s finished (%s)", task.id, task.type)
        except Exception as exc:
            _append_task_log(log_path, f"task failed: {exc}")
            LOG.exception("Task %s failed", task.id)
            task.status = "FAILED"
            task.step = "FAILED"
            task.error = str(exc)
            if (
                task.rollback_info
                and rollback_model is not None
                and rollback_target_type
                and task.target_type == rollback_target_type
            ):
                try:
                    env = rollback_model.objects.get(pk=task.target_id)
                    for key, value in (task.rollback_info or {}).items():
                        setattr(env, key, value)
                    env.save(update_fields=list(task.rollback_info.keys()))
                    LOG.info("Task %s rollback applied (%s)", task.id, task.rollback_info)
                except Exception:
                    LOG.exception("Task %s rollback failed", task.id)
        task.save(update_fields=["status", "step", "result", "error", "updated_at"])

    thread = Thread(target=runner, daemon=True)
    thread.start()
