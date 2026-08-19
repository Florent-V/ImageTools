import tempfile
from pathlib import Path

from app.engine.video.runner import run_ffmpeg

FRAME_TIMEOUT_S = 15
PREVIEW_TIMESTAMP_S = 1.0


async def extract_frame(path: Path, timestamp_s: float) -> bytes:
    """A single JPEG frame at the given timestamp."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
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
        return out_path.read_bytes()
    finally:
        out_path.unlink(missing_ok=True)


async def extract_preview_frame(path: Path, duration_s: float) -> bytes:
    """A single JPEG frame, taken near the start (or the midpoint of very short clips)."""
    timestamp = min(PREVIEW_TIMESTAMP_S, duration_s / 2)
    return await extract_frame(path, timestamp)
