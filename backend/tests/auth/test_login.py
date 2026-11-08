import hashlib
from urllib.parse import parse_qs, urlparse

import pytest

from .conftest import ISSUER, ORIGIN, USER_ID, USER_SUB

pytestmark = pytest.mark.anyio


async def test_login_redirects_with_pkce_s256(env):
    response = await env.client.get("/auth/login")
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(f"{ISSUER}/authorize?")
    query = parse_qs(urlparse(location).query)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) == 43
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == [f"{ORIGIN}/auth/callback"]


async def test_login_then_callback_opens_a_session(env):
    response = await env.login("/crop?x=1")
    assert response.status_code == 302
    assert response.headers["location"] == "/crop?x=1"
    me = await env.client.get("/api/me")
    assert me.status_code == 200
    assert me.json() == {"sub": USER_SUB, "id": USER_ID, "name": "alice", "email": USER_SUB, "roles": []}
    assert me.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("return_to", ["//evil.com", "https://evil.com", "/\\evil.com", "evil", "/\r\nx", ""])
async def test_malicious_return_to_is_replaced(env, return_to):
    response = await env.login(return_to)
    assert response.headers["location"] == "/"


async def test_unknown_state_is_rejected(env):
    response = await env.client.get("/auth/callback", params={"code": "x", "state": "unknown"})
    assert response.status_code == 400
    assert not env.sessions()


async def test_replayed_state_is_rejected(env):
    login = await env.client.get("/auth/login")
    callback = env.server.authorize(login.headers["location"])
    assert (await env.client.get(callback)).status_code == 302
    assert (await env.client.get(callback)).status_code == 400


async def test_expired_state_is_rejected(env):
    login = await env.client.get("/auth/login")
    env.db().execute("UPDATE login_attempts SET expires_at = expires_at - 601")
    response = await env.client.get(env.server.authorize(login.headers["location"]))
    assert response.status_code == 400


async def test_server_error_is_shown_without_loop(env):
    response = await env.client.get("/auth/callback", params={"error": "access_denied", "state": "x"})
    assert response.status_code == 302
    assert response.headers["location"] == "/?auth_error=access_denied"


async def test_iss_is_checked_when_announced(env):
    env.server.metadata["authorization_response_iss_parameter_supported"] = True
    await env.auth.client.discovery.refresh()

    login = await env.client.get("/auth/login")
    callback = env.server.authorize(login.headers["location"])
    assert (await env.client.get(callback + "&iss=https://evil.test")).status_code == 400

    login = await env.client.get("/auth/login")
    callback = env.server.authorize(login.headers["location"])
    assert (await env.client.get(callback + f"&iss={ISSUER}")).status_code == 302


async def test_session_id_changes_at_each_login(env):
    await env.login()
    first = env.client.cookies["__Host-session"]
    await env.login()
    second = env.client.cookies["__Host-session"]
    assert first != second
    # The previous session is dropped, not left behind
    assert [row["id_hash"] for row in env.sessions()] == [hashlib.sha256(second.encode()).hexdigest()]


async def test_cookie_attributes_and_content(env):
    response = await env.login()
    set_cookie = response.headers["set-cookie"]
    name_value, *attributes = [part.strip() for part in set_cookie.split(";")]
    name, value = name_value.split("=", 1)
    assert name == "__Host-session"
    assert {a.lower() for a in attributes} >= {"httponly", "secure", "samesite=lax", "path=/"}
    assert not any(a.lower().startswith("domain") for a in attributes)

    row = env.sessions()[0]
    # Opaque random id: no token in it, and only its hash is stored
    assert value not in (row["access_token"], row["refresh_token"])
    assert row["id_hash"] == hashlib.sha256(value.encode()).hexdigest()
    assert value not in str(dict(row))
