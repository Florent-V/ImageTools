"""Pure ASGI middleware (no BaseHTTPMiddleware): the session is checked before
anything reads the request body. FastAPI parses multipart bodies before
running dependencies, so a dependency alone would receive a whole 200 MB
unauthenticated upload before answering 401."""

import asyncio
from typing import TYPE_CHECKING, Any

from starlette.datastructures import Headers
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from . import csrf
from .client import GrantRevoked, ServerUnavailable
from .store import Session, now

if TYPE_CHECKING:
    from . import Auth

TOUCH_EVERY_S = 60
REVALIDATION_LEASE_S = 30


def error(status: int, code: str) -> Response:
    return JSONResponse({"error": code}, status_code=status, headers={"Cache-Control": "no-store"})


class AuthMiddleware:
    def __init__(self, app: ASGIApp, auth: "Auth", protected_prefixes: tuple[str, ...], public_paths: frozenset[str]) -> None:
        self.app = app
        self.auth = auth
        self.protected_prefixes = protected_prefixes
        self.public_paths = public_paths
        # One refresh per session within this worker; the DB lease covers the other workers
        self._inflight: dict[str, asyncio.Task] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        if csrf.needs_check(scope["method"], path) and not csrf.is_same_origin(
            Headers(scope=scope), self.auth.settings.public_origin
        ):
            await error(403, "csrf")(scope, receive, send)
            return

        if path.startswith(self.protected_prefixes) and path not in self.public_paths:
            result = await self.authenticate(scope)
            if isinstance(result, Response):
                await result(scope, receive, send)
                return
            scope.setdefault("state", {})["user"] = result

        await self.app(scope, receive, send)

    async def authenticate(self, scope: Scope) -> dict[str, Any] | Response:
        settings = self.auth.settings
        store = self.auth.store
        session_id = HTTPConnection(scope).cookies.get(settings.cookie_name)
        session = await store.get_session(session_id) if session_id else None
        if session is None:
            return error(401, "unauthenticated")

        ts = now()
        idle_expired = ts - session.last_seen_at > settings.session_idle_ttl.total_seconds()
        if idle_expired or ts >= session.absolute_expires_at:
            await store.delete_session(session.id_hash)
            return error(401, "unauthenticated")

        if ts - session.last_revalidated_at >= settings.session_revalidate_interval.total_seconds():
            failure = await self._revalidate_once(session)
            if failure is not None:
                return failure

        if ts - session.last_seen_at >= TOUCH_EVERY_S:
            await store.touch(session.id_hash)
        return session.user

    async def _revalidate_once(self, session: Session) -> Response | None:
        task = self._inflight.get(session.id_hash)
        if task is None:
            task = asyncio.ensure_future(self._revalidate(session))
            self._inflight[session.id_hash] = task
            task.add_done_callback(lambda _: self._inflight.pop(session.id_hash, None))
        # shield: a client disconnecting mustn't cancel a refresh other requests wait on
        return await asyncio.shield(task)

    async def _revalidate(self, session: Session) -> Response | None:
        """Refresh the tokens: proves the user still has access. None = carry on."""
        store = self.auth.store
        if not self.auth.client.discovery.ready:
            return error(503, "oauth_unavailable")
        interval = int(self.auth.settings.session_revalidate_interval.total_seconds())
        if not await store.claim_revalidation(session.id_hash, interval, REVALIDATION_LEASE_S):
            # Another worker is refreshing (or just did): its outcome applies on the next request
            return None
        if not session.refresh_token:
            await store.delete_session(session.id_hash)
            return error(401, "unauthenticated")
        try:
            token = await self.auth.client.refresh(session.refresh_token)
        except GrantRevoked:
            await store.delete_session(session.id_hash)
            return error(401, "unauthenticated")
        except ServerUnavailable:
            # Keep the session, but don't serve on an unrenewed token: retry next request
            await store.release_revalidation(session.id_hash)
            return error(503, "oauth_unavailable")
        await store.save_tokens(session.id_hash, token, session.refresh_token)
        return None
