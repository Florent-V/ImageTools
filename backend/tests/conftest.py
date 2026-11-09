import os
import tempfile

import pytest

# app.main reads AuthSettings at import: give it a configuration. No OAuth
# server is contacted: the TestClients below don't run the lifespan.
os.environ.setdefault("OAUTH_ISSUER", "https://auth.test")
os.environ.setdefault("OAUTH_CLIENT_ID", "app-test")
os.environ.setdefault("OAUTH_CLIENT_SECRET", "secret-test")
os.environ.setdefault("PUBLIC_ORIGIN", "http://testserver")
os.environ.setdefault("SESSION_DB_PATH", os.path.join(tempfile.mkdtemp(), "sessions.db"))
os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("COOKIE_SECURE", "false")


@pytest.fixture(autouse=True)
def _authenticated(request, monkeypatch):
    """Outside tests/auth/, the suite runs as an already-authenticated user:
    the session cookie value *is* the user, "test-user" when there is no cookie.
    The session machinery itself is covered by tests/auth."""
    if ".auth." in request.module.__name__:
        return
    from app.auth import csrf
    from app.auth.deps import AuthUser
    from app.main import auth

    async def fake_authenticate(ctx, session_id):
        return AuthUser(sub=session_id or "test-user", name="Test", email="test@example.com")

    monkeypatch.setattr("app.auth.middleware.authenticate", fake_authenticate)
    monkeypatch.setattr(csrf, "needs_check", lambda method, path: False)
    monkeypatch.setattr(auth.discovery, "metadata", {"issuer": auth.settings.oauth_issuer})
