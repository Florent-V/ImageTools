import asyncio
from io import BytesIO

from PIL import Image

from app.engine.video.frame import extract_frame, extract_preview_frame
from tests import video_factories


def test_extract_preview_frame_returns_a_valid_jpeg_at_source_resolution(tmp_path):
    data = video_factories.make_video_bytes(duration_s=2.0, width=160, height=120)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    frame_bytes = asyncio.run(extract_preview_frame(path, duration_s=2.0))

    image = Image.open(BytesIO(frame_bytes))
    assert image.format == "JPEG"
    assert image.size == (160, 120)


def test_extract_preview_frame_handles_very_short_clips(tmp_path):
    data = video_factories.make_video_bytes(duration_s=0.5, width=160, height=120)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    frame_bytes = asyncio.run(extract_preview_frame(path, duration_s=0.5))

    assert len(frame_bytes) > 0


def test_extract_frame_at_arbitrary_timestamp_returns_valid_jpeg(tmp_path):
    data = video_factories.make_video_bytes(duration_s=3.0, width=160, height=120)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    frame_bytes = asyncio.run(extract_frame(path, timestamp_s=2.0))

    image = Image.open(BytesIO(frame_bytes))
    assert image.format == "JPEG"
    assert image.size == (160, 120)
