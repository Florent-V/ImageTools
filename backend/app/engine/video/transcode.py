import tempfile
from pathlib import Path

from app.engine.video.presets import CRF_BY_QUALITY
from app.engine.video.runner import run_ffmpeg
from app.schemas.video import VideoCropRect, VideoOutputSpec

# container id -> (file suffix, ffmpeg muxer -f value, video codec args, audio codec args)
_CONTAINER_SPECS: dict[str, tuple[str, str, list[str], list[str]]] = {
    "mp4": (".mp4", "mp4", ["-c:v", "libx264", "-preset", "veryfast"], ["-c:a", "aac", "-b:a", "128k"]),
    "mov": (".mov", "mov", ["-c:v", "libx264", "-preset", "veryfast"], ["-c:a", "aac", "-b:a", "128k"]),
    "mkv": (".mkv", "matroska", ["-c:v", "libx264", "-preset", "veryfast"], ["-c:a", "aac", "-b:a", "128k"]),
    "webm": (".webm", "webm", ["-c:v", "libvpx-vp9", "-b:v", "0"], ["-c:a", "libopus"]),
}


async def transcode(
    path: Path,
    crop: VideoCropRect | None,
    output: VideoOutputSpec,
    timeout_s: float,
) -> bytes:
    filters = []
    if crop is not None:
        filters.append(f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y}")
    filters.append(f"scale={output.resolution_width}:{output.resolution_height}")
    if output.fps != "original":
        filters.append(f"fps={output.fps}")

    crf = CRF_BY_QUALITY[output.quality]
    suffix, muxer, video_codec_args, audio_codec_args = _CONTAINER_SPECS[output.container]

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(path),
            "-vf", ",".join(filters),
            *video_codec_args,
            "-crf", str(crf),
            *audio_codec_args,
        ]
        if output.container in ("mp4", "mov"):
            cmd += ["-movflags", "+faststart"]
        cmd += ["-f", muxer, str(out_path)]
        await run_ffmpeg(cmd, timeout_s=timeout_s)
        return out_path.read_bytes()
    finally:
        out_path.unlink(missing_ok=True)
