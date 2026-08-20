from io import BytesIO

from fastapi import APIRouter, File, Form, Response, UploadFile
from PIL import Image, UnidentifiedImageError

from app.api._shared import parse_body, read_upload, run_with_timeout
from app.concurrency import job_semaphore
from app.config import settings
from app.engine.decoder import READ_FORMATS, check_pixel_limit
from app.engine.encoder import FILE_EXTENSION, MEDIA_TYPE
from app.engine.pipeline import process
from app.engine.presets import PRESETS
from app.errors import ImageError
from app.schemas.request import ProcessRequest

router = APIRouter(prefix="/api")

GPS_IFD = 0x8825


async def _read_image_upload(file: UploadFile) -> bytes:
    return await read_upload(file, settings.max_file_size_bytes, settings.max_file_size_mb, "FILE_TOO_LARGE")


@router.post("/process")
async def process_image(
    file: UploadFile = File(...),
    request: str = Form(...),
    watermark_file: UploadFile | None = File(None),
) -> Response:
    parsed = parse_body(ProcessRequest, request)

    data = await _read_image_upload(file)
    watermark_data = await _read_image_upload(watermark_file) if watermark_file is not None else None

    async with job_semaphore:
        result = await run_with_timeout(
            process, data, parsed, watermark_data, timeout_s=settings.request_timeout_s
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
    data = await _read_image_upload(file)

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

    check_pixel_limit(image.width, image.height)

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
