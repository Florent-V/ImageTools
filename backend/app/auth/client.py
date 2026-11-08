"""OAuth client: Authlib AsyncOAuth2Client (authorization URL, code exchange,
refresh, revocation, userinfo). Also the single shared HTTP client.

Not authlib.integrations.starlette_client: it keeps its state in Starlette's
SessionMiddleware, a signed cookie that can't be revoked.
"""

import logging
import warnings
from typing import Any

import httpx

with warnings.catch_warnings():
    # Authlib >= 1.7 prefers the httpx2 package and warns when it falls back to httpx
    warnings.simplefilter("ignore")
    from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuthError

from .config import AuthSettings
from .discovery import Discovery

logger = logging.getLogger("auth.client")

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
# Token endpoint refusals that mean the grant is gone for good
FATAL_ERRORS = {"invalid_grant", "invalid_client", "unauthorized_client"}


class GrantRevoked(Exception):
    """The server refused the code or refresh token: the session must end."""


class ServerUnavailable(Exception):
    """Network error, timeout or 5xx: keep the session, try again later."""


class OAuthClient:
    def __init__(self, settings: AuthSettings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.http = AsyncOAuth2Client(
            client_id=settings.oauth_client_id,
            client_secret=settings.oauth_client_secret.get_secret_value(),
            scope=settings.oauth_scopes,
            redirect_uri=settings.redirect_uri,
            code_challenge_method="S256",
            timeout=TIMEOUT,
            transport=transport,
        )
        self.discovery = Discovery(settings, self.http)

    async def aclose(self) -> None:
        await self.http.aclose()

    def _configure(self) -> None:
        self.http.token_endpoint_auth_method = self.discovery.token_endpoint_auth_method

    def authorization_url(self, state: str, code_verifier: str, nonce: str | None) -> str:
        extra = {"nonce": nonce} if nonce else {}
        url, _ = self.http.create_authorization_url(
            self.discovery["authorization_endpoint"], state=state, code_verifier=code_verifier, **extra
        )
        return url

    async def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        return await self._token_request(
            self.http.fetch_token,
            self.discovery["token_endpoint"],
            grant_type="authorization_code",
            code=code,
            code_verifier=code_verifier,
            redirect_uri=self.settings.redirect_uri,
        )

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        token = await self._token_request(
            self.http.refresh_token, self.discovery["token_endpoint"], refresh_token=refresh_token
        )
        # Authlib returns the client's own token attribute: copy it before the next await
        return dict(token)

    async def _token_request(self, call, url: str, **kwargs) -> dict[str, Any]:
        self._configure()
        try:
            token = await call(url, **kwargs)
        except OAuthError as exc:
            if exc.error in FATAL_ERRORS:
                raise GrantRevoked(exc.error) from exc
            raise ServerUnavailable(exc.error) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 401):
                raise GrantRevoked(str(exc.response.status_code)) from exc
            raise ServerUnavailable(str(exc)) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ServerUnavailable(str(exc)) from exc
        return dict(token)

    async def userinfo(self, access_token: str) -> dict[str, Any] | None:
        """None when the server publishes no userinfo endpoint. Raises
        GrantRevoked on 401/403 (no access to this app)."""
        url = self.discovery.get("userinfo_endpoint")
        if not url:
            return None
        try:
            response = await self.http.request(
                "GET", url, headers={"Authorization": f"Bearer {access_token}"}, withhold_token=True
            )
        except httpx.HTTPError as exc:
            raise ServerUnavailable(str(exc)) from exc
        if response.status_code in (401, 403):
            raise GrantRevoked("access_denied" if response.status_code == 403 else "invalid_token")
        if response.status_code != 200:
            raise ServerUnavailable(f"userinfo HTTP {response.status_code}")
        return response.json()

    async def revoke(self, refresh_token: str) -> None:
        """Best effort (RFC 7009): a failure is logged, never raised."""
        url = self.discovery.get("revocation_endpoint")
        if not url:
            return
        self._configure()
        self.http.revocation_endpoint_auth_method = self.http.token_endpoint_auth_method
        try:
            response = await self.http.revoke_token(url, token=refresh_token, token_type_hint="refresh_token")  # noqa: S106 (RFC 7009 parameter, not a password)
            if response.status_code >= 400:
                logger.warning("refresh token revocation refused: HTTP %s", response.status_code)
        except httpx.HTTPError as exc:
            logger.warning("refresh token revocation failed: %s", exc)
