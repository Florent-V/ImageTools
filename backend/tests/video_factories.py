"""Test videos generated via ffmpeg itself. Nothing is committed as a binary fixture."""

import subprocess
import tempfile
from pathlib import Path


def make_video_bytes(duration_s: float = 2.0, width: int = 320, height: int = 240, fps: int = 15) -> bytes:
    """A short synthetic H.264 MP4, generated with ffmpeg's built-in test source."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"testsrc=duration={duration_s}:size={width}x{height}:rate={fps}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
        return out_path.read_bytes()
    finally:
        out_path.unlink(missing_ok=True)


def make_non_video_bytes() -> bytes:
    """Garbage bytes — not a video at all, for unsupported-format tests."""
    return b"not a real video file, just plain bytes"
