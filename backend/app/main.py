import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.pwa_routes import router as pwa_router
from app.api.video_routes import router as video_router
from app.errors import ImageError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("imagetools")

app = FastAPI(title="ImageTools", docs_url="/api/docs", openapi_url="/api/openapi.json")

# Only needed when the browser reaches this API on a different origin than
# the frontend it's served from (e.g. prod-remote's direct-port access).
# Same-origin setups (dev proxy, prod-home/prod-remote behind Caddy) never
# trigger a CORS check, so this is a no-op for them.
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(pwa_router)
app.include_router(video_router)


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
                "message": "The image could not be processed",
                "detail": {},
            }
        },
    )


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
