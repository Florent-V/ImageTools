import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.api.pwa_routes import router as pwa_router
from app.api.routes import router
from app.api.video_routes import router as video_router
from app.auth import setup_auth
from app.auth.config import AuthSettings
from app.errors import ImageError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("imagetools")

app = FastAPI(title="ImageTools", docs_url="/api/docs", openapi_url="/api/openapi.json")

# This backend is the OAuth client (BFF): server-side sessions, opaque cookie.
# The middleware answers 401 before any upload body is read and exposes the
# user as request.state.user. Same origin as the front (behind Caddy): no CORS.
auth = setup_auth(app, AuthSettings(), protected_prefixes=("/api",), public_paths=("/api/health",))
for _router in (router, pwa_router, video_router):
    app.include_router(_router)


@app.middleware("http")
async def log_timing(request: Request, call_next):
    """Log the shape of the work, never its content.

    No filename, no image bytes, no client address — the whole point of
    this project is that nothing identifying is retained.
    """
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "%s %s status=%s duration_ms=%.1f out=%sx%s format=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        response.headers.get("X-Output-Width", "-"),
        response.headers.get("X-Output-Height", "-"),
        response.headers.get("X-Output-Extension", "-"),
    )
    return response


@app.exception_handler(ImageError)
async def image_error_handler(request: Request, exc: ImageError) -> JSONResponse:
    logger.info("%s error_code=%s", request.url.path, exc.code)
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload())


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "PROCESSING_FAILED",
                "message": "The request could not be processed",
                "detail": {},
            }
        },
    )


@app.get("/api/health")
async def health() -> Response:
    # 503 until the OAuth server metadata is loaded: not ready to log anyone in
    if not auth.discovery.ready:
        return JSONResponse({"status": "starting"}, status_code=503)
    return JSONResponse({"status": "ok"})
