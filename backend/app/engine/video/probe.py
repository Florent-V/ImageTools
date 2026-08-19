import json
from dataclasses import dataclass
from pathlib import Path

from app.engine.video.runner import run_ffmpeg

PROBE_TIMEOUT_S = 15


@dataclass
class VideoInfo:
    duration_s: float
    width: int
    height: int
    format: str


async def probe(path: Path) -> VideoInfo:
    stdout = await run_ffmpeg(
        [
            "ffprobe", "-v", "error",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(path),
        ],
        timeout_s=PROBE_TIMEOUT_S,
    )
    data = json.loads(stdout)
    streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not streams:
        raise ValueError("no video stream found")
    stream = streams[0]
    duration = data.get("format", {}).get("duration")
    if duration is None:
        raise ValueError("duration not reported")
    return VideoInfo(
        duration_s=float(duration),
        width=int(stream["width"]),
        height=int(stream["height"]),
        format=data.get("format", {}).get("format_name", ""),
    )
