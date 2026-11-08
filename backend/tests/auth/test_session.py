import asyncio

import pytest

from .conftest import ORIGIN

pytestmark = pytest.mark.anyio

SAME_ORIGIN = {"Origin": ORIGIN}


async def test_protected_route_without_session_is_401(env):
    response = await env.client.get("/api/data")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthenticated"}


async def test_public_path_stays_open(env):
    assert (await env.client.get("/api/health")).status_code == 200


async def test_unknown_cookie_is_401(env):
    env.client.cookies.set("__Host-session", "forged")
    assert (await env.client.get("/api/data")).status_code == 401


async def test_unauthenticated_upload_is_refused_before_reading_the_body(env):
    received = []
    sent = []

    async def receive():
        received.append(True)
        return {"type": "http.request", "body": b"x" * 1024, "more_body": True}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/upload",
        "raw_path": b"/api/upload",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"app.test"),
            (b"origin", ORIGIN.encode()),
            (b"content-type", b"multipart/form-data; boundary=x"),
            (b"content-length", str(200 * 1024 * 1024).encode()),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("app.test", 443),
    }
    await env.app(scope, receive, send)

    assert sent[0]["status"] == 401
    assert received == []


async def test_idle_session_expires(env):
    await env.login()
    env.age_sessions(last_seen_at=8 * 3600 + 1)
    assert (await env.client.get("/api/data")).status_code == 401
    assert not env.sessions()


async def test_absolute_lifetime_is_enforced(env):
    await env.login()
    env.age_sessions(absolute_expires_at=7 * 86400)
    assert (await env.client.get("/api/data")).status_code == 401
    assert not env.sessions()


async def test_fresh_session_is_not_revalidated(env):
    await env.login()
    assert (await env.client.get("/api/data")).status_code == 200
    assert env.server.refresh_calls == 0


async def test_revalidation_rotates_the_tokens(env):
    await env.login()
    before = env.sessions()[0]
    env.age_sessions(last_revalidated_at=15 * 60)

    assert (await env.client.get("/api/data")).status_code == 200
    after = env.sessions()[0]
    assert env.server.refresh_calls == 1
    assert after["refresh_token"] != before["refresh_token"]
    assert after["access_token"] != before["access_token"]
    assert after["last_revalidated_at"] > before["last_revalidated_at"] - 15 * 60


async def test_revoked_grant_closes_the_session(env):
    await env.login()
    env.age_sessions(last_revalidated_at=15 * 60)
    env.server.refresh_error = "invalid_grant"
    assert (await env.client.get("/api/data")).status_code == 401
    assert not env.sessions()


@pytest.mark.parametrize("failure", ["network", 503])
async def test_unavailable_server_keeps_the_session(env, failure):
    await env.login()
    env.age_sessions(last_revalidated_at=15 * 60)
    if failure == "network":
        env.server.down = True
    else:
        env.server.refresh_error = failure

    response = await env.client.get("/api/data")
    assert response.status_code == 503
    assert len(env.sessions()) == 1

    # Back up: the next request refreshes and goes through
    env.server.down = False
    env.server.refresh_error = None
    assert (await env.client.get("/api/data")).status_code == 200


async def test_concurrent_requests_refresh_once(env):
    await env.login()
    env.age_sessions(last_revalidated_at=15 * 60)
    env.server.refresh_delay = 0.05

    responses = await asyncio.gather(*(env.client.get("/api/data") for _ in range(10)))
    assert [r.status_code for r in responses] == [200] * 10
    assert env.server.refresh_calls == 1


async def test_lease_held_by_another_worker_skips_refresh(env):
    await env.login()
    env.age_sessions(last_revalidated_at=15 * 60)
    env.db().execute("UPDATE sessions SET revalidating_until = strftime('%s','now') + 30")
    assert (await env.client.get("/api/data")).status_code == 200
    assert env.server.refresh_calls == 0


# ── CSRF ───────────────────────────────────────────────────────────────


async def test_foreign_origin_is_403(env):
    await env.login()
    response = await env.client.post("/api/upload", content=b"x", headers={"Origin": "https://evil.test"})
    assert response.status_code == 403


async def test_missing_origin_and_fetch_metadata_is_403(env):
    await env.login()
    assert (await env.client.post("/api/upload", content=b"x")).status_code == 403


async def test_sec_fetch_site_same_origin_is_accepted(env):
    await env.login()
    response = await env.client.post("/api/upload", content=b"abc", headers={"Sec-Fetch-Site": "same-origin"})
    assert response.status_code == 200
    assert response.json() == {"size": 3}


async def test_same_origin_post_is_accepted(env):
    await env.login()
    assert (await env.client.post("/api/upload", content=b"x", headers=SAME_ORIGIN)).status_code == 200


async def test_logout_requires_same_origin(env):
    await env.login()
    assert (await env.client.post("/auth/logout", headers={"Origin": "https://evil.test"})).status_code == 403
    assert len(env.sessions()) == 1


# ── logout ─────────────────────────────────────────────────────────────


async def test_logout_closes_the_session(env):
    await env.login()
    cookie = env.client.cookies["__Host-session"]
    response = await env.client.post("/auth/logout", headers=SAME_ORIGIN)

    assert response.status_code == 200
    assert response.json() == {"redirect": "/logged-out"}
    assert '__Host-session=""' in response.headers["set-cookie"]
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert not env.sessions()
    env.client.cookies.set("__Host-session", cookie)
    assert (await env.client.get("/api/data")).status_code == 401


async def test_logout_revokes_the_refresh_token(env):
    env.server.metadata["revocation_endpoint"] = "https://auth.test/revoke"
    env.server.metadata["end_session_endpoint"] = "https://auth.test/logout"
    await env.auth.client.discovery.refresh()
    await env.login()
    refresh_token = env.sessions()[0]["refresh_token"]

    response = await env.client.post("/auth/logout", headers=SAME_ORIGIN)
    assert response.json() == {"redirect": "https://auth.test/logout"}
    assert env.server.revocations == [refresh_token]


async def test_logout_succeeds_when_revocation_fails(env):
    env.server.metadata["revocation_endpoint"] = "https://auth.test/revoke"
    await env.auth.client.discovery.refresh()
    await env.login()
    env.server.revocation_status = 500

    response = await env.client.post("/auth/logout", headers=SAME_ORIGIN)
    assert response.status_code == 200
    assert not env.sessions()


async def test_logout_without_session_is_harmless(env):
    response = await env.client.post("/auth/logout", headers=SAME_ORIGIN)
    assert response.status_code == 200
