from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rest_framework import status
from rest_framework.response import Response


@dataclass
class AuthCheckResult:
    ok: bool
    user: Any = None
    response: Response | None = None


def ensure_authenticated_user(request) -> AuthCheckResult:
    """
    Defensive authentication guard.

    DRF permissions should already block anonymous requests, but several legacy
    viewsets access request.user directly and may still receive AnonymousUser in
    edge paths. This helper keeps those endpoints stable and predictable.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return AuthCheckResult(
            ok=False,
            response=Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            ),
        )
    return AuthCheckResult(ok=True, user=user)

