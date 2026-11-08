"""OAuth server metadata (RFC 8414): fetched at startup, validated, cached in
memory and refreshed in the background."""

import asyncio
import logging
from typing import Any

import httpx

from .config import AuthSettings

logger = logging.getLogger("auth.discovery")

WELL_KNOWN = ("/.well-known/oauth-authorization-server", "/.well-known/openid-configuration")
SUPPORTED_AUTH_METHODS = ("client_secret_basic", "client_secret_post")


class DiscoveryError(Exception):
    """The server answered, but its metadata can't be used: the app must not start."""


class Discovery:
    refresh_interval_s = 3600
    # Retry delays while the server is unreachable (startup, then not-ready loop)
    retry_delays_s: tuple[float, ...] = (1, 2, 4, 8, 16)
    not_ready_retry_s = 30

    def __init__(self, settings: AuthSettings, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.http = http
        self.metadata: dict[str, Any] | None = None

    @property
    def ready(self) -> bool:
        return self.metadata is not None

    def get(self, key: str) -> Any:
        return self.metadata.get(key) if self.metadata else None

    def __getitem__(self, key: str) -> Any:
        if self.metadata is None:
            raise RuntimeError("OAuth server metadata not loaded yet")
        return self.metadata[key]

    @property
    def token_endpoint_auth_method(self) -> str:
        supported = self.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"]
        return next(m for m in supported if m in SUPPORTED_AUTH_METHODS)

    async def fetch(self) -> dict[str, Any]:
        """Fetch and validate the metadata. Raises DiscoveryError (unusable
        metadata) or httpx.HTTPError (server unreachable / failing)."""
        issuer = self.settings.oauth_issuer
        response = None
        for path in WELL_KNOWN:
            response = await self.http.request("GET", f"{issuer.rstrip('/')}{path}", withhold_token=True)
            if response.status_code != 404:
                break
        response.raise_for_status()
        metadata = response.json()
        self.validate(metadata)
        return metadata

    def validate(self, metadata: Any) -> None:
        settings = self.settings
        if not isinstance(metadata, dict):
            raise DiscoveryError("metadata is not a JSON object")
        if metadata.get("issuer") != settings.oauth_issuer:
            raise DiscoveryError(
                f"issuer mismatch: server says {metadata.get('issuer')!r}, OAUTH_ISSUER is {settings.oauth_issuer!r}"
            )
        if "S256" not in (metadata.get("code_challenge_methods_supported") or []):
            raise DiscoveryError("server does not support PKCE S256")
        for key in ("authorization_endpoint", "token_endpoint"):
            url = metadata.get(key)
            if not url:
                raise DiscoveryError(f"{key} missing")
            if settings.app_env != "dev" and not url.startswith("https://"):
                raise DiscoveryError(f"{key} must be https: {url}")
        if not metadata.get("jwks_uri") and settings.oauth_logout_token_secret is None:
            raise DiscoveryError("no jwks_uri: OAUTH_LOGOUT_TOKEN_SECRET is required to verify logout tokens")
        supported = metadata.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"]
        if not any(m in SUPPORTED_AUTH_METHODS for m in supported):
            raise DiscoveryError(f"no supported client authentication method in {supported}")

    async def load(self) -> None:
        """Startup: retry while unreachable; DiscoveryError propagates."""
        for attempt, delay in enumerate((*self.retry_delays_s, None), start=1):
            try:
                self.metadata = await self.fetch()
                logger.info("OAuth server metadata loaded from %s", self.settings.oauth_issuer)
                return
            except httpx.HTTPError as exc:
                logger.warning("OAuth server unreachable (attempt %d): %s", attempt, exc)
                if delay is not None:
                    await asyncio.sleep(delay)
        logger.error("OAuth server still unreachable: not ready, retrying in the background")

    async def refresh(self) -> None:
        """Background refresh: a failure keeps the previous metadata."""
        try:
            self.metadata = await self.fetch()
        except (httpx.HTTPError, DiscoveryError, ValueError) as exc:
            logger.warning("OAuth metadata refresh failed, keeping the cached copy: %s", exc)

    async def refresh_forever(self) -> None:
        while True:
            await asyncio.sleep(self.refresh_interval_s if self.ready else self.not_ready_retry_s)
            await self.refresh()
