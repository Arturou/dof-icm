"""Authentication seam: the app depends on AuthBackend, never on a provider.

Three backends are available:

- ``ClerkAuthBackend`` (clerk_auth.py) — production multi-user auth. Imported
  lazily by ``app.build_default_app`` because airclerk validates its
  environment variables at import time.
- ``LocalAuthBackend`` — single-admin local auth for self-hosted DOF-ICM
  instances without Clerk. Anyone who completes the password login becomes the
  configured admin user, so the quota / review / publish / feedback flows can
  all be exercised on one machine.
- ``FakeAuthBackend`` — header-driven backend for tests and scripted access
  (send ``X-Eval-User``/``X-Eval-Role``).
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Protocol

from starlette.requests import Request

ROLE_ADMIN = "admin"
ROLE_USER = "user"


@dataclass(frozen=True)
class User:
    id: str
    role: str = ROLE_USER
    email: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


class AuthBackend(Protocol):
    """Resolve the current request to a user, or None when anonymous."""

    async def get_user(self, request: Request) -> User | None: ...


class FakeAuthBackend:
    """Header-driven backend for tests and local development without Clerk.

    Send ``X-Eval-User: <id>`` and optionally ``X-Eval-Role: admin``.
    Requests without the header are anonymous.
    """

    def __init__(self, users: dict[str, User] | None = None):
        self.users = dict(users or {})

    async def get_user(self, request: Request) -> User | None:
        user_id = request.headers.get("x-eval-user")
        if not user_id:
            return None
        known = self.users.get(user_id)
        if known is not None:
            return known
        role = request.headers.get("x-eval-role", ROLE_USER)
        return User(id=user_id, role=role)


class LocalAuthBackend:
    """Single-admin password auth, sessions in the signed cookie.

    The sign-in/out routes are added by ``app.create_app`` when it sees a
    backend with ``local = True``. Use it for a self-hosted instance on your
    own machine or tailnet; for a public multi-user deployment configure
    Clerk (``DOF_AUTH_BACKEND=clerk``) instead.
    """

    local = True

    def __init__(self, *, email: str, password: str):
        self.email = email
        self.password = password
        self._admin = User(id=email, role=ROLE_ADMIN, email=email)

    @property
    def admin_user(self) -> User:
        return self._admin

    def check_password(self, submitted: str | None) -> bool:
        if not self.password or not submitted:
            return False
        return hmac.compare_digest(self.password.encode(), submitted.encode())

    async def get_user(self, request: Request) -> User | None:
        if request.session.get("local_admin_user") == self.email:
            return self._admin
        return None

    def sign_in(self, request: Request) -> None:
        request.session["local_admin_user"] = self.email

    def sign_out(self, request: Request) -> None:
        request.session.pop("local_admin_user", None)
