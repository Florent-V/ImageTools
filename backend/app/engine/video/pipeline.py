from pathlib import Path

from app.config import settings
from app.engine.operations.crop import validate_bounds
from app.engine.video import probe, transcode
from app.engine.video.runner import FfmpegError
from app.engine.video.tempfiles import temp_video_file
from app.errors import ImageError
from app.schemas.video import VideoProcessRequest


async def validate_video(path: Path) -> probe.VideoInfo:
    try:
        info = await probe.probe(path)
    except (ValueError, FfmpegError):
        raise ImageError("UNSUPPORTED_VIDEO_FORMAT", "Unrecognised or unreadable video file")

    if info.duration_s > settings.max_video_duration_s:
        raise ImageError(
            "VIDEO_TOO_LONG",
            f"Video exceeds the {settings.max_video_duration_s}s limit",
            duration_s=info.duration_s,
        )
    return info


async def process_video(data: bytes, request: VideoProcessRequest) -> bytes:
    """Write once, validate, crop-check, transcode — mirrors engine/pipeline.py's
    shape for images, so the two verticals stop diverging in thickness."""
    with temp_video_file(data) as path:
        info = await validate_video(path)
        if request.crop is not None:
            validate_bounds(
                request.crop.x, request.crop.y, request.crop.width, request.crop.height,
                info.width, info.height,
            )
        try:
            return await transcode.transcode(path, request.crop, request.output, timeout_s=settings.video_timeout_s)
        except FfmpegError:
            raise ImageError("VIDEO_PROCESSING_FAILED", "The video could not be processed")
