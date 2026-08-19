import asyncio
import json

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.engine.decoder import decode
from app.engine.pwa.generator import GeneratedKit, generate_kit
from app.errors import ImageError
from app.schemas.pwa import PwaGenerateRequest

router = APIRouter(prefix="/api/pwa")


async def _read_upload(file: UploadFile) -> bytes:
    """Read the body, refusing anything past the limit without buffering it all."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > settings.max_file_size_bytes:
            raise ImageError(
                "FILE_TOO_LARGE",
                f"File exceeds the {settings.max_file_size_mb} MB limit",
                limit_bytes=settings.max_file_size_bytes,
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/generate")
async def generate_pwa_kit(
    file: UploadFile = File(...),
    request: str = Form(...),
) -> Response:
    try:
        parsed = PwaGenerateRequest.model_validate(json.loads(request))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ImageError("INVALID_OPERATION", "The request payload is invalid", reason=str(exc))

    data = await _read_upload(file)

    def _build() -> GeneratedKit:
        decoded = decode(data)
        return generate_kit(decoded.image, parsed)

    try:
        kit = await asyncio.wait_for(
            run_in_threadpool(_build),
            timeout=settings.request_timeout_s,
        )
    except asyncio.TimeoutError:
        raise ImageError(
            "PROCESSING_FAILED",
            f"Processing exceeded the {settings.request_timeout_s}s limit",
        )

    return Response(
        content=kit.zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="pwa-assets.zip"',
            "X-File-Count": str(kit.file_count),
        },
    )
