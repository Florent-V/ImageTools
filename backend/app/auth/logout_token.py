"""Back-channel logout token verification (OpenID Connect Back-Channel Logout 1.0 §2.6)."""

import time
from typing import Any

import jwt
from starlette.concurrency import run_in_threadpool

from .config import AuthSettings
from .discovery import Discovery
from .store import SessionStore

EVENT = "http://schemas.openid.net/event/backchannel-logout"
# Used when the server doesn't list its signing algorithms. Never "none", never HMAC.
ASYMMETRIC_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512", "EdDSA"]
IAT_MAX_SKEW_S = 300


class LogoutTokenError(Exception):
    pass


class LogoutTokenVerifier:
    def __init__(self, settings: AuthSettings, discovery: Discovery, store: SessionStore) -> None:
        self.settings = settings
        self.discovery = discovery
        self.store = store
        self._jwk_client: jwt.PyJWKClient | None = None

    def jwks(self, uri: str) -> jwt.PyJWKClient:
        # Caches the keys; an unknown kid triggers one JWKS reload (key rotation)
        if self._jwk_client is None or self._jwk_client.uri != uri:
            self._jwk_client = jwt.PyJWKClient(uri, cache_keys=True, lifespan=3600)
        return self._jwk_client

    async def _key_and_algorithms(self, token: str) -> tuple[Any, list[str]]:
        jwks_uri = self.discovery.get("jwks_uri")
        if jwks_uri:
            try:
                signing_key = await run_in_threadpool(self.jwks(jwks_uri).get_signing_key_from_jwt, token)
            except jwt.PyJWTError as exc:
                raise LogoutTokenError(f"signing key: {exc}") from exc
            advertised = self.discovery.get("id_token_signing_alg_values_supported")
            algorithms = [a for a in (advertised or ASYMMETRIC_ALGORITHMS) if a in ASYMMETRIC_ALGORITHMS]
            return signing_key.key, algorithms
        if self.settings.oauth_logout_token_secret is not None:
            return self.settings.oauth_logout_token_secret.get_secret_value(), ["HS256"]
        raise LogoutTokenError("no key to verify logout tokens")

    async def verify(self, token: str) -> dict[str, Any]:
        key, algorithms = await self._key_and_algorithms(token)
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=algorithms,
                audience=self.settings.oauth_client_id,
                issuer=self.settings.oauth_issuer,
                leeway=60,
                options={"require": ["iss", "aud", "iat", "jti", "events"]},
            )
        except jwt.PyJWTError as exc:
            raise LogoutTokenError(str(exc)) from exc

        if abs(time.time() - claims["iat"]) > IAT_MAX_SKEW_S:
            raise LogoutTokenError("iat too old or in the future")
        events = claims.get("events")
        if not isinstance(events, dict) or EVENT not in events:
            raise LogoutTokenError("missing back-channel logout event")
        if "nonce" in claims:
            raise LogoutTokenError("nonce is forbidden in a logout token")
        if not claims.get("sub") and not claims.get("sid"):
            raise LogoutTokenError("sub or sid required")
        expires_at = int(claims.get("exp") or time.time() + 2 * IAT_MAX_SKEW_S)
        if not await self.store.remember_jti(str(claims["jti"]), expires_at):
            raise LogoutTokenError("replayed jti")
        return claims
