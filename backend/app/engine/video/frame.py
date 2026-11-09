from pathlib import Path

from app.engine.video.runner import FfmpegError, run_ffmpeg
from app.engine.video.tempfiles import temp_output_path

FRAME_TIMEOUT_S = 15
PREVIEW_TIMESTAMP_S = 1.0
# Seeking at (or past) the very end yields no frame on ffmpeg >= 8: stay just before it.
END_MARGIN_S = 0.1


def clamp_timestamp(timestamp_s: float, duration_s: float) -> float:
    return max(0.0, min(timestamp_s, duration_s - END_MARGIN_S))


async def extract_frame(path: Path, timestamp_s: float) -> bytes:
    """A single JPEG frame at the given timestamp."""
    with temp_output_path(".jpg") as out_path:
        await run_ffmpeg(
            [
                "ffmpeg", "-y",
                "-ss", str(timestamp_s),
                "-i", str(path),
                "-frames:v", "1",
                "-f", "image2",
                str(out_path),
            ],
            timeout_s=FRAME_TIMEOUT_S,
        )
        if not out_path.exists() or out_path.stat().st_size == 0:
            raise FfmpegError(f"no frame produced at {timestamp_s}s")
        return out_path.read_bytes()


async def extract_preview_frame(path: Path, duration_s: float) -> bytes:
    """A single JPEG frame, taken near the start (or the midpoint of very short clips)."""
    timestamp = min(PREVIEW_TIMESTAMP_S, duration_s / 2)
    return await extract_frame(path, timestamp)
