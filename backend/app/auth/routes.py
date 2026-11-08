"""/auth/login, /auth/callback, /auth/logout, /auth/backchannel-logout, /api/me."""

import logging
import secrets
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

from .client import GrantRevoked, ServerUnavailable
from .deps import current_user
from .logout_token import ASYMMETRIC_ALGORITHMS, LogoutTokenError
from .store import hash_id

if TYPE_CHECKING:
    from . import Auth

logger = logging.getLogger("auth.routes")

LOGIN_ATTEMPT_TTL_S = 600
NO_STORE = {"Cache-Control": "no-store"}


def safe_return_to(value: str | None) -> str:
    """Local paths only: no //host, no /\\host, no scheme, no control characters."""
    if (
        not value
        or not value.startswith("/")
        or value.startswith(("//", "/\\"))
        or any(ord(c) < 0x20 or c == "\x7f" for c in value)
    ):
        return "/"
    return value


def auth_error(code: str) -> RedirectResponse:
    # The front shows the error instead of starting a new login (no loop)
    return RedirectResponse(f"/?auth_error={quote(code)}", status_code=302, headers=NO_STORE)


def make_router(auth: "Auth") -> APIRouter:
    settings = auth.settings
    store = auth.store
    client = auth.client
    discovery = client.discovery
    router = APIRouter()

    def unavailable() -> Response:
        return JSONResponse({"error": "oauth_unavailable"}, status_code=503, headers=NO_STORE)

    @router.get("/auth/login", include_in_schema=False)
    async def login(return_to: str | None = None) -> Response:
        if not discovery.ready:
            return unavailable()
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        nonce = secrets.token_urlsafe(32) if "openid" in settings.scopes else None
        await store.add_login_attempt(state, code_verifier, nonce, safe_return_to(return_to), LOGIN_ATTEMPT_TTL_S)
        return RedirectResponse(client.authorization_url(state, code_verifier, nonce), status_code=302, headers=NO_STORE)

    @router.get("/auth/callback", include_in_schema=False)
    async def callback(request: Request) -> Response:
        params = request.query_params
        if params.get("error"):
            return auth_error(params["error"])
        if not discovery.ready:
            return unavailable()
        # RFC 9207: only when the server announces it
        if discovery.get("authorization_response_iss_parameter_supported") and params.get("iss") != settings.oauth_issuer:
            return JSONResponse({"error": "invalid_issuer"}, status_code=400, headers=NO_STORE)
        attempt = await store.consume_login_attempt(params.get("state", ""))
        if attempt is None or not params.get("code"):
            return JSONResponse({"error": "invalid_state"}, status_code=400, headers=NO_STORE)

        try:
            token = await client.exchange_code(params["code"], attempt.code_verifier)
            user = await identify(token, attempt.nonce)
        except GrantRevoked as exc:
            logger.info("login refused by the OAuth server: %s", exc)
            return auth_error("access_denied")
        except (ServerUnavailable, jwt.PyJWTError, ValueError) as exc:
            logger.warning("login failed: %s", exc)
            return auth_error("server_error")

        # Fresh session id at every login (session fixation); the previous one is dropped
        previous = request.cookies.get(settings.cookie_name)
        if previous:
            await store.delete_session(hash_id(previous))
        session_id = await store.create_session(
            user["sub"], user.pop("_sid", None), user, token, int(settings.session_absolute_ttl.total_seconds())
        )
        response = RedirectResponse(attempt.return_to, status_code=302, headers=NO_STORE)
        response.set_cookie(
            settings.cookie_name,
            session_id,
            max_age=int(settings.session_absolute_ttl.total_seconds()),
            path="/",
            secure=settings.cookie_secure,
            httponly=True,
            samesite="lax",
        )
        return response

    async def identify(token: dict[str, Any], nonce: str | None) -> dict[str, Any]:
        """id_token if any, else userinfo, else the access token if it's a verifiable JWT."""
        if token.get("id_token") and discovery.get("jwks_uri"):
            claims = await verify_jwt(token["id_token"])
            if nonce and claims.get("nonce") != nonce:
                raise ValueError("id_token nonce mismatch")
            claims["_sid"] = claims.get("sid")
            return user_from(claims)
        info = await client.userinfo(token["access_token"])
        if info is not None:
            return user_from(info)
        if discovery.get("jwks_uri"):
            return user_from(await verify_jwt(token["access_token"], issuer=False))
        raise ValueError("no way to identify the user")

    async def verify_jwt(value: str, issuer: bool = True) -> dict[str, Any]:
        signing_key = await run_in_threadpool(auth.verifier.jwks(discovery["jwks_uri"]).get_signing_key_from_jwt, value)
        if signing_key.algorithm_name not in ASYMMETRIC_ALGORITHMS:
            raise ValueError(f"unexpected signing algorithm {signing_key.algorithm_name}")
        return jwt.decode(
            value,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            audience=settings.oauth_client_id,
            issuer=settings.oauth_issuer if issuer else None,
            options={"require": ["exp", "sub"]},
        )

    def user_from(claims: dict[str, Any]) -> dict[str, Any]:
        if not claims.get("sub"):
            raise ValueError("no sub in the user claims")
        return {
            "sub": claims["sub"],
            # Stable id (UUID) when the server provides one; sub may change (e.g. an e-mail)
            "id": claims.get("id") or claims.get("uid") or claims["sub"],
            "name": claims.get("name") or claims.get("preferred_username"),
            "email": claims.get("email"),
            "roles": claims.get("roles") or [],
            "_sid": claims.get("_sid"),
        }

    @router.post("/auth/logout", include_in_schema=False)
    async def logout(request: Request) -> Response:
        # CSRF checked by the middleware
        session_id = request.cookies.get(settings.cookie_name)
        session = await store.delete_session(hash_id(session_id)) if session_id else None
        if session and session.refresh_token:
            await client.revoke(session.refresh_token)
        redirect = discovery.get("end_session_endpoint") or auth.post_logout_redirect
        response = JSONResponse({"redirect": redirect}, headers=NO_STORE)
        response.delete_cookie(settings.cookie_name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax")
        return response

    @router.post("/auth/backchannel-logout", include_in_schema=False)
    async def backchannel_logout(logout_token: str = Form("")) -> Response:
        # Called by the OAuth server, not a browser: no session, no CSRF; the signature is the proof
        try:
            claims = await auth.verifier.verify(logout_token)
        except LogoutTokenError as exc:
            logger.warning("logout token rejected: %s", exc)
            return JSONResponse({"error": "invalid_request"}, status_code=400, headers=NO_STORE)
        if claims.get("sid"):
            count = await store.delete_by_sid(claims["sid"])
        else:
            count = await store.delete_by_sub(claims["sub"])
        logger.info("back-channel logout: %d session(s) closed", count)
        return Response(status_code=200, headers=NO_STORE)

    @router.get("/api/me")
    async def me(user: dict[str, Any] = Depends(current_user)) -> Response:
        return JSONResponse(
            {key: user.get(key) for key in ("sub", "id", "name", "email", "roles")}, headers=NO_STORE
        )

    return router
