import pytest

from app.auth import DiscoveryError

from .conftest import ISSUER, build_app

pytestmark = pytest.mark.anyio


async def start(settings, server):
    app = build_app(settings, server)
    async with app.router.lifespan_context(app):
        return app.state.auth.ready


@pytest.mark.parametrize("issuer", [f"{ISSUER}/", "https://auth.tes", "https://AUTH.test"])
async def test_issuer_mismatch_blocks_startup(settings, server, issuer):
    server.metadata["issuer"] = issuer
    with pytest.raises(DiscoveryError, match="issuer"):
        await start(settings, server)


async def test_missing_s256_blocks_startup(settings, server):
    server.metadata["code_challenge_methods_supported"] = ["plain"]
    with pytest.raises(DiscoveryError, match="S256"):
        await start(settings, server)


async def test_http_endpoint_blocks_startup_in_prod(settings, server):
    server.metadata["token_endpoint"] = "http://auth.test/token"
    with pytest.raises(DiscoveryError, match="https"):
        await start(settings, server)


async def test_missing_jwks_uri_needs_a_logout_secret(settings, server):
    del server.metadata["jwks_uri"]
    with pytest.raises(DiscoveryError, match="jwks_uri"):
        await start(settings, server)


async def test_falls_back_to_openid_configuration(settings, server):
    server.rfc8414_missing = True
    assert await start(settings, server)


async def test_unreachable_server_starts_not_ready(settings, server):
    server.down = True
    assert await start(settings, server) is False


async def test_refresh_failure_keeps_the_cache(env):
    discovery = env.auth.client.discovery
    before = discovery.metadata
    env.server.down = True
    await discovery.refresh()
    assert discovery.metadata == before
    env.server.down = False
    env.server.metadata["issuer"] = "https://evil.test"
    await discovery.refresh()
    assert discovery.metadata == before


async def test_not_ready_refuses_login(settings, server):
    server.down = True
    app = build_app(settings, server)
    async with app.router.lifespan_context(app):
        import httpx

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://app.test") as client:
            assert (await client.get("/auth/login")).status_code == 503
