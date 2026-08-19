import base64
import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import ValidationError

from app.config import settings
from app.engine.video import frame, presets, probe, transcode
from app.engine.video.runner import FfmpegError
from app.errors import ImageError
from app.schemas.video import VideoProcessRequest

router = APIRouter(prefix="/api/video")


async def _read_upload(file: UploadFile) -> bytes:
    """Read the body, refusing anything past the video size limit without buffering it all."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > settings.max_video_file_size_bytes:
            raise ImageError(
                "VIDEO_TOO_LARGE",
                f"File exceeds the {settings.max_video_file_size_mb} MB limit",
                limit_bytes=settings.max_video_file_size_bytes,
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _write_temp(data: bytes, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        return Path(tmp.name)


async def _probe_and_validate(data: bytes) -> tuple[Path, probe.VideoInfo]:
    path = _write_temp(data, ".mp4")
    try:
        info = await probe.probe(path)
    except (ValueError, FfmpegError):
        path.unlink(missing_ok=True)
        raise ImageError("UNSUPPORTED_VIDEO_FORMAT", "Unrecognised or unreadable video file")

    if info.duration_s > settings.max_video_duration_s:
        path.unlink(missing_ok=True)
        raise ImageError(
            "VIDEO_TOO_LONG",
            f"Video exceeds the {settings.max_video_duration_s}s limit",
            duration_s=info.duration_s,
        )
    return path, info


@router.post("/inspect")
async def inspect_video(file: UploadFile = File(...)) -> dict:
    data = await _read_upload(file)
    path, info = await _probe_and_validate(data)
    try:
        frame_bytes = await frame.extract_preview_frame(path, info.duration_s)
    except FfmpegError:
        raise ImageError("VIDEO_PROCESSING_FAILED", "Could not extract a preview frame")
    finally:
        path.unlink(missing_ok=True)

    preview_data_uri = "data:image/jpeg;base64," + base64.b64encode(frame_bytes).decode("ascii")
    return {
        "duration_s": info.duration_s,
        "width": info.width,
        "height": info.height,
        "format": info.format,
        "size_bytes": len(data),
        "preview_frame": preview_data_uri,
    }


@router.post("/frame")
async def video_frame(file: UploadFile = File(...), timestamp_s: float = Form(...)) -> dict:
    data = await _read_upload(file)
    path, info = await _probe_and_validate(data)
    try:
        clamped = max(0.0, min(timestamp_s, info.duration_s))
        frame_bytes = await frame.extract_frame(path, clamped)
    except FfmpegError:
        raise ImageError("VIDEO_PROCESSING_FAILED", "Could not extract a preview frame")
    finally:
        path.unlink(missing_ok=True)

    return {"preview_frame": "data:image/jpeg;base64," + base64.b64encode(frame_bytes).decode("ascii")}


@router.post("/process")
async def process_video(
    file: UploadFile = File(...),
    request: str = Form(...),
) -> Response:
    try:
        parsed = VideoProcessRequest.model_validate(json.loads(request))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ImageError("INVALID_OPERATION", "The request payload is invalid", reason=str(exc))

    data = await _read_upload(file)
    path, info = await _probe_and_validate(data)

    if parsed.crop is not None:
        crop = parsed.crop
        if crop.x + crop.width > info.width or crop.y + crop.height > info.height:
            path.unlink(missing_ok=True)
            raise ImageError(
                "INVALID_OPERATION",
                "Crop rectangle does not fit inside the source video",
                source_width=info.width,
                source_height=info.height,
            )

    try:
        encoded = await transcode.transcode(
            path, parsed.crop, parsed.output, timeout_s=settings.video_timeout_s
        )
    except FfmpegError:
        raise ImageError("VIDEO_PROCESSING_FAILED", "The video could not be processed")
    finally:
        path.unlink(missing_ok=True)

    return Response(
        content=encoded,
        media_type="video/mp4",
        headers={
            "X-Output-Width": str(parsed.output.resolution_width),
            "X-Output-Height": str(parsed.output.resolution_height),
            "X-Output-Size": str(len(encoded)),
            "X-Input-Size": str(len(data)),
        },
    )


@router.get("/limits")
async def video_limits() -> dict:
    return {
        "max_file_size_mb": settings.max_video_file_size_mb,
        "max_duration_s": settings.max_video_duration_s,
    }


@router.get("/presets")
async def video_presets() -> dict:
    return {
        "ratios": [
            {"id": p.id, "label": p.label, "description": p.description, "ratio": list(p.ratio) if p.ratio else None}
            for p in presets.RATIO_PRESETS
        ],
        "resolution_ladder": [{"label": label, "height": height} for label, height in presets.RESOLUTION_LADDER],
        "containers": [{"id": cid, "label": label} for cid, label in presets.CONTAINERS],
        "fps": presets.FPS_OPTIONS,
        "quality": list(presets.CRF_BY_QUALITY.keys()),
    }
