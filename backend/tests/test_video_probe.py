import asyncio

import pytest

from app.engine.video.probe import probe
from tests import video_factories


def test_probe_reads_duration_and_dimensions(tmp_path):
    data = video_factories.make_video_bytes(duration_s=2.0, width=320, height=240)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    info = asyncio.run(probe(path))

    assert info.width == 320
    assert info.height == 240
    assert 1.5 < info.duration_s < 2.5


def test_probe_raises_on_garbage_input(tmp_path):
    path = tmp_path / "not-a-video.bin"
    path.write_bytes(video_factories.make_non_video_bytes())

    with pytest.raises(Exception):
        asyncio.run(probe(path))
