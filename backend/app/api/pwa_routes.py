from fastapi import APIRouter, File, Form, Response, UploadFile

from app.api._shared import parse_body, read_upload, run_with_timeout
from app.concurrency import job_semaphore
from app.config import settings
from app.engine.decoder import decode
from app.engine.pwa.generator import GeneratedKit, generate_kit
from app.schemas.pwa import PwaGenerateRequest

router = APIRouter(prefix="/api/pwa")


@router.post("/generate")
async def generate_pwa_kit(
    file: UploadFile = File(...),
    request: str = Form(...),
) -> Response:
    parsed = parse_body(PwaGenerateRequest, request)
    data = await read_upload(file, settings.max_file_size_bytes, settings.max_file_size_mb, "FILE_TOO_LARGE")

    def _build() -> GeneratedKit:
        decoded = decode(data)
        return generate_kit(decoded.image, parsed)

    async with job_semaphore:
        kit = await run_with_timeout(_build, timeout_s=settings.request_timeout_s)

    return Response(
        content=kit.zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="pwa-assets.zip"',
            "X-File-Count": str(kit.file_count),
        },
    )
