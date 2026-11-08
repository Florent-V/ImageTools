"""Fake OAuth server (discovery, JWKS, token, userinfo, revocation) and an
app-agnostic FastAPI app wired with setup_auth()."""

import asyncio
import base64
import hashlib
import secrets
import sqlite3
import time
import uuid
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from jwt.algorithms import RSAAlgorithm

from app.auth import AuthSettings, setup_auth
from app.auth.discovery import Discovery

ISSUER = "https://auth.test"
ORIGIN = "https://app.test"
CLIENT_ID = "app-client"
CLIENT_SECRET = "app-secret"
USER_SUB = "alice@example.com"
USER_ID = "0198f1c2-7a3b-7c4d-8e5f-0a1b2c3d4e5f"
EVENT = "http://schemas.openid.net/event/backchannel-logout"


class FakeOAuthServer:
    def __init__(self) -> None:
        self.keys: dict[str, rsa.RSAPrivateKey] = {}
        self.active_kid = self.add_key()
        self.metadata = {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "userinfo_endpoint": f"{ISSUER}/api/userinfo",
            "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
            "scopes_supported": ["profile", "email"],
            "backchannel_logout_supported": True,
            "authorization_response_iss_parameter_supported": False,
        }
        self.down = False
        self.rfc8414_missing = False
        self.codes: dict[str, str] = {}
        self.access_tokens: set[str] = set()
        self.refresh_tokens: set[str] = set()
        self.refresh_calls = 0
        self.refresh_delay = 0.0
        self.refresh_error: str | int | None = None
        self.revocations: list[str] = []
        self.revocation_status = 200
        self.jwks_fetches = 0

    # ── keys and tokens ─────────────────────────────────────────────────

    def add_key(self) -> str:
        kid = f"key-{len(self.keys) + 1}"
        self.keys[kid] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return kid

    def jwks(self) -> dict:
        self.jwks_fetches += 1
        keys = []
        for kid, key in self.keys.items():
            jwk = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
            keys.append({**jwk, "kid": kid, "alg": "RS256", "use": "sig"})
        return {"keys": keys}

    def sign(self, claims: dict, kid: str | None = None, key: rsa.RSAPrivateKey | None = None) -> str:
        kid = kid or self.active_kid
        return jwt.encode(claims, key or self.keys[kid], algorithm="RS256", headers={"kid": kid, "typ": "logout+jwt"})

    def logout_token(self, drop: tuple[str, ...] = (), kid: str | None = None, key=None, **overrides) -> str:
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": USER_SUB,
            "uid": USER_ID,
            "iat": now,
            "exp": now + 120,
            "jti": uuid.uuid4().hex,
            "events": {EVENT: {}},
            **overrides,
        }
        for name in drop:
            claims.pop(name, None)
        return self.sign(claims, kid=kid, key=key)

    def _issue(self) -> dict:
        access, refresh = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
        self.access_tokens.add(access)
        self.refresh_tokens.add(refresh)
        return {"access_token": access, "refresh_token": refresh, "token_type": "Bearer", "expires_in": 900}

    # ── browser side ────────────────────────────────────────────────────

    def authorize(self, authorization_url: str) -> str:
        """The user signs in: returns the app callback path with code and state."""
        query = parse_qs(urlparse(authorization_url).query)
        assert query["code_challenge_method"] == ["S256"]
        assert query["client_id"] == [CLIENT_ID]
        assert query["redirect_uri"] == [f"{ORIGIN}/auth/callback"]
        code = secrets.token_urlsafe(16)
        self.codes[code] = query["code_challenge"][0]
        return "/auth/callback?" + urlencode({"code": code, "state": query["state"][0]})

    # ── HTTP side ───────────────────────────────────────────────────────

    async def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("connection refused", request=request)
        path = request.url.path
        if path == "/.well-known/oauth-authorization-server":
            if self.rfc8414_missing:
                return httpx.Response(404)
            return httpx.Response(200, json=self.metadata)
        if path == "/.well-known/openid-configuration":
            return httpx.Response(200, json=self.metadata)
        if path == "/token":
            return await self._token(request)
        if path == "/api/userinfo":
            bearer = request.headers.get("authorization", "").removeprefix("Bearer ")
            if bearer not in self.access_tokens:
                return httpx.Response(401, json={"error": "invalid_token"})
            return httpx.Response(200, json={"sub": USER_SUB, "id": USER_ID, "name": "alice", "email": USER_SUB})
        if path == "/revoke":
            self.revocations.append(parse_qs(request.content.decode())["token"][0])
            return httpx.Response(self.revocation_status)
        return httpx.Response(404)

    async def _token(self, request: httpx.Request) -> httpx.Response:
        expected = "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        if request.headers.get("authorization") != expected:
            return httpx.Response(401, json={"error": "invalid_client"})
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        if form["grant_type"] == "authorization_code":
            challenge = self.codes.pop(form.get("code", ""), None)
            verifier_hash = base64.urlsafe_b64encode(hashlib.sha256(form["code_verifier"].encode()).digest())
            if challenge is None or verifier_hash.rstrip(b"=").decode() != challenge:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json=self._issue())
        if form["grant_type"] == "refresh_token":
            self.refresh_calls += 1
            await asyncio.sleep(self.refresh_delay)
            if isinstance(self.refresh_error, int):
                return httpx.Response(self.refresh_error, text="upstream error")
            if self.refresh_error or form["refresh_token"] not in self.refresh_tokens:
                return httpx.Response(400, json={"error": self.refresh_error or "invalid_grant"})
            self.refresh_tokens.discard(form["refresh_token"])  # rotation: single use
            return httpx.Response(200, json=self._issue())
        return httpx.Response(400, json={"error": "unsupported_grant_type"})


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def server(monkeypatch) -> FakeOAuthServer:
    fake = FakeOAuthServer()
    # PyJWKClient fetches with urllib: serve it the fake JWKS
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: fake.jwks())
    monkeypatch.setattr(Discovery, "retry_delays_s", (0, 0))
    return fake


@pytest.fixture
def settings(tmp_path) -> AuthSettings:
    return AuthSettings(
        oauth_issuer=ISSUER,
        oauth_client_id=CLIENT_ID,
        oauth_client_secret=CLIENT_SECRET,
        public_origin=ORIGIN,
        session_db_path=tmp_path / "sessions.db",
    )


def build_app(settings: AuthSettings, server: FakeOAuthServer) -> FastAPI:
    app = FastAPI()
    setup_auth(
        app,
        settings,
        protected_prefixes=["/api/"],
        public_paths=["/api/health"],
        post_logout_redirect="/logged-out",
        transport=httpx.MockTransport(server.handle),
    )

    @app.get("/api/health")
    async def health():
        return {"ready": app.state.auth.ready}

    @app.get("/api/data")
    async def data(request: Request):
        return {"sub": request.state.user["sub"]}

    @app.post("/api/upload")
    async def upload(request: Request):
        return {"size": len(await request.body())}

    return app


class Env:
    def __init__(self, app: FastAPI, server: FakeOAuthServer, client: httpx.AsyncClient) -> None:
        self.app = app
        self.server = server
        self.client = client
        self.auth = app.state.auth

    async def login(self, return_to: str | None = None) -> httpx.Response:
        params = {"return_to": return_to} if return_to is not None else {}
        response = await self.client.get("/auth/login", params=params)
        assert response.status_code == 302
        return await self.client.get(self.server.authorize(response.headers["location"]))

    def db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.auth.settings.session_db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def sessions(self) -> list[sqlite3.Row]:
        return self.db().execute("SELECT * FROM sessions").fetchall()

    def age_sessions(self, **columns: int) -> None:
        """Move timestamps back: age_sessions(last_seen_at=3600) = seen 1 h ago."""
        for column, seconds in columns.items():
            self.db().execute(f"UPDATE sessions SET {column} = {column} - ?", (seconds,))


@pytest.fixture
async def env(settings, server):
    app = build_app(settings, server)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            yield Env(app, server, client)
