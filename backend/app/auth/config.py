"""Authentication settings, read from the environment (no prefix).

Only OAUTH_ISSUER, OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET describe the OAuth
server: every endpoint URL comes from its discovery document.
"""

from datetime import timedelta
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    # Exact issuer of the OAuth server (compared as a string, trailing slash included)
    oauth_issuer: str
    oauth_client_id: str
    oauth_client_secret: SecretStr
    oauth_scopes: str = "profile email"
    # Public origin of this app (https://pdf.example.com): redirect URI and CSRF check
    public_origin: str

    session_db_path: Path = Path("/data/sessions.db")
    # Durations: seconds or ISO 8601 (PT8H)
    session_idle_ttl: timedelta = timedelta(hours=8)
    session_absolute_ttl: timedelta = timedelta(days=7)
    session_revalidate_interval: timedelta = timedelta(minutes=15)
    # Empty = "__Host-session" in prod, "session" in dev. Set it in dev when
    # several apps share localhost: browsers don't isolate cookies by port.
    session_cookie_name: str = ""
    cookie_secure: bool = True
    app_env: Literal["prod", "dev"] = "prod"
    # Only if the server signs logout tokens with HS256 and publishes no jwks_uri
    oauth_logout_token_secret: SecretStr | None = None

    @field_validator("public_origin")
    @classmethod
    def _strip_origin(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _secure_in_prod(self) -> "AuthSettings":
        if not self.cookie_secure and self.app_env == "prod":
            raise ValueError("COOKIE_SECURE=false is only allowed with APP_ENV=dev")
        return self

    @property
    def redirect_uri(self) -> str:
        return f"{self.public_origin}/auth/callback"

    @property
    def cookie_name(self) -> str:
        if self.session_cookie_name:
            return self.session_cookie_name
        return "__Host-session" if self.cookie_secure else "session"

    @property
    def scopes(self) -> list[str]:
        return self.oauth_scopes.split()
