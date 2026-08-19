import asyncio
import json
from io import BytesIO

from fastapi import APIRouter, File, Form, Response, UploadFile
from starlette.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from app.config import settings
from app.engine.decoder import READ_FORMATS
from app.engine.encoder import FILE_EXTENSION, MEDIA_TYPE
from app.engine.pipeline import process
from app.engine.presets import PRESETS
from app.errors import ImageError
from app.schemas.request import ProcessRequest

router = APIRouter(prefix="/api")

GPS_IFD = 0x8825


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


@router.post("/process")
async def process_image(
    file: UploadFile = File(...),
    request: str = Form(...),
    watermark_file: UploadFile | None = File(None),
) -> Response:
    try:
        parsed = ProcessRequest.model_validate(json.loads(request))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ImageError("INVALID_OPERATION", "The request payload is invalid", reason=str(exc))

    data = await _read_upload(file)
    watermark_data = await _read_upload(watermark_file) if watermark_file is not None else None
    # wait_for bounds the client's wait but cannot kill the running thread —
    # the CPU work continues to completion in the pool (a known Python limit).
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(process, data, parsed, watermark_data),
            timeout=settings.request_timeout_s,
        )
    except asyncio.TimeoutError:
        raise ImageError(
            "PROCESSING_FAILED",
            f"Processing exceeded the {settings.request_timeout_s}s limit",
        )

    return Response(
        content=result.data,
        media_type=MEDIA_TYPE[result.format],
        headers={
            "X-Output-Width": str(result.width),
            "X-Output-Height": str(result.height),
            "X-Output-Size": str(result.output_size),
            "X-Input-Size": str(result.input_size),
            "X-Output-Quality": str(result.quality),
            "X-Output-Extension": FILE_EXTENSION[result.format],
        },
    )


@router.get("/formats")
async def formats() -> dict:
    return {
        "read": sorted(READ_FORMATS),
        "write": sorted(MEDIA_TYPE),
        "presets": PRESETS,
        "limits": {
            "max_file_size_mb": settings.max_file_size_mb,
            "max_megapixels": settings.max_megapixels,
        },
    }


@router.post("/inspect")
async def inspect(file: UploadFile = File(...)) -> dict:
    data = await _read_upload(file)

    try:
        image = Image.open(BytesIO(data))
    except Image.DecompressionBombError:
        raise ImageError(
            "IMAGE_TOO_LARGE",
            "The image header declares implausibly large dimensions",
        )
    except (UnidentifiedImageError, OSError):
        raise ImageError("UNSUPPORTED_FORMAT", "Unrecognised image format")

    if image.format not in READ_FORMATS:
        raise ImageError("UNSUPPORTED_FORMAT", f"{image.format} files cannot be read")

    exif = image.getexif()
    return {
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "size_bytes": len(data),
        "has_exif": bool(exif),
        "has_gps": bool(exif.get_ifd(GPS_IFD)) if exif else False,
        "has_icc": image.info.get("icc_profile") is not None,
    }
