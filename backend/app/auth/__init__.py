"""OAuth client (BFF) for a FastAPI app: discovery, login with PKCE, server-side
sessions in SQLite, periodic revalidation, back-channel logout.

Nothing in this package is specific to the app: keep it identical in every
repository that uses it (diff -r must be empty) and bump AUTH_MODULE_VERSION
on any change. App-specific values are setup_auth() arguments.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Iterable

import httpx
from fastapi import FastAPI

from .client import OAuthClient
from .config import AuthSettings
from .deps import current_user
from .discovery import DiscoveryError
from .logout_token import LogoutTokenVerifier
from .middleware import AuthMiddleware
from .routes import make_router
from .store import SessionStore

AUTH_MODULE_VERSION = "2.0.0"

__all__ = ["AUTH_MODULE_VERSION", "Auth", "AuthSettings", "DiscoveryError", "auth_ready", "current_user", "setup_auth"]

logger = logging.getLogger("auth")

PURGE_EVERY_S = 600


class Auth:
    def __init__(self, settings: AuthSettings, post_logout_redirect: str, transport: httpx.AsyncBaseTransport | None) -> None:
        self.settings = settings
        self.post_logout_redirect = post_logout_redirect
        self.store = SessionStore(settings.session_db_path)
        self.client = OAuthClient(settings, transport)
        self.verifier = LogoutTokenVerifier(settings, self.client.discovery, self.store)

    @property
    def ready(self) -> bool:
        return self.client.discovery.ready

    @contextlib.asynccontextmanager
    async def running(self) -> AsyncIterator[None]:
        self.store.init()
        try:
            await self.client.discovery.load()
            tasks = [
                asyncio.create_task(self.client.discovery.refresh_forever()),
                asyncio.create_task(self._purge_forever()),
            ]
            try:
                yield
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            await self.client.aclose()

    async def _purge_forever(self) -> None:
        idle_s = int(self.settings.session_idle_ttl.total_seconds())
        while True:
            await asyncio.sleep(PURGE_EVERY_S)
            try:
                await self.store.purge()
                await self.store.purge_idle(idle_s)
            except Exception:
                logger.exception("session purge failed")


def setup_auth(
    app: FastAPI,
    settings: AuthSettings,
    protected_prefixes: Iterable[str],
    public_paths: Iterable[str] = (),
    *,
    post_logout_redirect: str = "/",
    transport: httpx.AsyncBaseTransport | None = None,
) -> Auth:
    """Wire the auth into the app: middleware, /auth/* and /api/me routes,
    discovery and background tasks in the lifespan.

    post_logout_redirect: where the browser goes after logout when the server
    publishes no end_session_endpoint. transport: tests only.
    """
    auth = Auth(settings, post_logout_redirect, transport)
    app.state.auth = auth
    app.add_middleware(
        AuthMiddleware,
        auth=auth,
        protected_prefixes=tuple(protected_prefixes),
        public_paths=frozenset(public_paths),
    )
    app.include_router(make_router(auth))

    previous_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def lifespan(app_: FastAPI):
        async with auth.running(), previous_lifespan(app_) as state:
            yield state

    app.router.lifespan_context = lifespan
    return auth


def auth_ready(app: FastAPI) -> bool:
    """For the health check: 503 until the OAuth server metadata is loaded."""
    auth = getattr(app.state, "auth", None)
    return auth is not None and auth.ready
