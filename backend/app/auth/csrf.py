"""CSRF: state-changing requests must come from our own origin. No CORS at all."""

from collections.abc import Mapping

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
EXEMPT_PATHS = {"/auth/backchannel-logout"}


def needs_check(method: str, path: str) -> bool:
    if method not in UNSAFE_METHODS or path in EXEMPT_PATHS:
        return False
    return path.startswith("/api/") or path == "/auth/logout"


def is_same_origin(headers: Mapping[str, str], public_origin: str) -> bool:
    origin = headers.get("origin")
    if origin is not None:
        return origin == public_origin
    return headers.get("sec-fetch-site") == "same-origin"
