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


@pytest.fixture(autouse=True)
def _authenticated(request, monkeypatch):
    """Outside tests/auth/, the suite runs as an already-authenticated user,
    from the same origin."""
    if "tests/auth/" in str(request.path).replace(os.sep, "/"):
        return
    from app.auth.middleware import AuthMiddleware

    async def authenticate(self, scope):
        return {"sub": "user@test", "id": "test-user", "name": "Test", "email": "user@test", "roles": []}

    monkeypatch.setattr(AuthMiddleware, "authenticate", authenticate)
    monkeypatch.setattr("app.auth.csrf.is_same_origin", lambda headers, origin: True)
