import base64

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.api._shared import parse_body, read_upload
from app.concurrency import job_semaphore
from app.config import settings
from app.engine.video import frame, pipeline, presets
from app.engine.video.runner import FfmpegError
from app.engine.video.tempfiles import temp_video_file
from app.errors import ImageError
from app.schemas.video import VideoProcessRequest

router = APIRouter(prefix="/api/video")


async def _read_video_upload(file: UploadFile) -> bytes:
    return await read_upload(file, settings.max_video_file_size_bytes, settings.max_video_file_size_mb, "VIDEO_TOO_LARGE")


@router.post("/inspect")
async def inspect_video(file: UploadFile = File(...)) -> dict:
    data = await _read_video_upload(file)
    with temp_video_file(data) as path:
        info = await pipeline.validate_video(path)
        try:
            frame_bytes = await frame.extract_preview_frame(path, info.duration_s)
        except FfmpegError:
            raise ImageError("VIDEO_PROCESSING_FAILED", "Could not extract a preview frame")

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
    data = await _read_video_upload(file)
    with temp_video_file(data) as path:
        info = await pipeline.validate_video(path)
        try:
            clamped = frame.clamp_timestamp(timestamp_s, info.duration_s)
            frame_bytes = await frame.extract_frame(path, clamped)
        except FfmpegError:
            raise ImageError("VIDEO_PROCESSING_FAILED", "Could not extract a preview frame")

    return {"preview_frame": "data:image/jpeg;base64," + base64.b64encode(frame_bytes).decode("ascii")}


@router.post("/process")
async def process_video(
    file: UploadFile = File(...),
    request: str = Form(...),
) -> Response:
    parsed = parse_body(VideoProcessRequest, request)
    data = await _read_video_upload(file)

    async with job_semaphore:
        encoded = await pipeline.process_video(data, parsed)

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
