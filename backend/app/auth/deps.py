from typing import Any

from fastapi import HTTPException, Request


def current_user(request: Request) -> dict[str, Any]:
    """The user set by AuthMiddleware. Raises 401 if the route was left outside
    the protected prefixes by mistake."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return user
