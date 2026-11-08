import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from .conftest import CLIENT_ID, ISSUER, USER_SUB

pytestmark = pytest.mark.anyio


async def post(env, token, **headers):
    return await env.client.post("/auth/backchannel-logout", data={"logout_token": token}, headers=headers)


async def test_valid_token_closes_the_user_sessions_by_sub(env):
    await env.login()
    await env.login()  # same browser: replaces the first one
    env.db().execute(
        "INSERT INTO sessions SELECT 'other', sub, NULL, user_claims, NULL, NULL, NULL, created_at,"
        " last_seen_at, last_revalidated_at, absolute_expires_at, 0 FROM sessions"
    )
    env.db().execute(
        "INSERT INTO sessions SELECT 'bob', 'bob@example.com', NULL, user_claims, NULL, NULL, NULL, created_at,"
        " last_seen_at, last_revalidated_at, absolute_expires_at, 0 FROM sessions LIMIT 1"
    )

    response = await post(env, env.server.logout_token())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert [row["sub"] for row in env.sessions()] == ["bob@example.com"]
    assert (await env.client.get("/api/data")).status_code == 401


async def test_sid_targets_one_session(env):
    await env.login()
    env.db().execute("UPDATE sessions SET oauth_sid = 'sid-1'")
    env.db().execute(
        "INSERT INTO sessions SELECT 'other', sub, 'sid-2', user_claims, NULL, NULL, NULL, created_at,"
        " last_seen_at, last_revalidated_at, absolute_expires_at, 0 FROM sessions"
    )
    assert (await post(env, env.server.logout_token(sid="sid-1"))).status_code == 200
    assert [row["oauth_sid"] for row in env.sessions()] == ["sid-2"]


async def test_exempt_from_csrf(env):
    response = await post(env, env.server.logout_token(), Origin="https://auth.test")
    assert response.status_code == 200


def unsigned(claims: dict) -> str:
    return jwt.encode(claims, None, algorithm="none")


INVALID = {
    "wrong-signature": lambda s: s.logout_token(key=rsa.generate_private_key(public_exponent=65537, key_size=2048)),
    "alg-none": lambda s: unsigned({"iss": ISSUER, "aud": CLIENT_ID, "sub": USER_SUB, "iat": int(time.time()),
                                    "jti": "x", "events": {"http://schemas.openid.net/event/backchannel-logout": {}}}),
    "unknown-kid": lambda s: s.logout_token(kid="nope", key=s.keys[s.active_kid]),
    "wrong-aud": lambda s: s.logout_token(aud="another-app"),
    "wrong-iss": lambda s: s.logout_token(iss="https://evil.test"),
    "iss-trailing-slash": lambda s: s.logout_token(iss=f"{ISSUER}/"),
    "nonce": lambda s: s.logout_token(nonce="n"),
    "no-events": lambda s: s.logout_token(drop=("events",)),
    "wrong-event": lambda s: s.logout_token(events={"other": {}}),
    "no-sub-nor-sid": lambda s: s.logout_token(drop=("sub",)),
    "expired": lambda s: s.logout_token(exp=int(time.time()) - 120),
    "old-iat": lambda s: s.logout_token(iat=int(time.time()) - 600, exp=int(time.time()) + 60),
    "no-jti": lambda s: s.logout_token(drop=("jti",)),
    "garbage": lambda s: "not-a-jwt",
    "empty": lambda s: "",
}


@pytest.mark.parametrize("case", INVALID)
async def test_invalid_tokens_are_rejected(env, case):
    await env.login()
    response = await post(env, INVALID[case](env.server))
    assert response.status_code == 400
    assert len(env.sessions()) == 1


async def test_replayed_jti_is_rejected(env):
    token = env.server.logout_token()
    assert (await post(env, token)).status_code == 200
    await env.login()
    assert (await post(env, token)).status_code == 400
    assert len(env.sessions()) == 1


async def test_key_rotation_is_picked_up_without_restart(env):
    await env.login()
    assert (await post(env, env.server.logout_token())).status_code == 200
    env.server.active_kid = env.server.add_key()
    await env.login()
    assert (await post(env, env.server.logout_token())).status_code == 200
    assert not env.sessions()
