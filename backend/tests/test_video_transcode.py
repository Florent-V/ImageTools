import asyncio

from app.engine.video.probe import probe
from app.engine.video.transcode import transcode
from app.schemas.video import VideoCropRect, VideoOutputSpec
from tests import video_factories


def test_transcode_crops_and_scales_to_the_requested_resolution(tmp_path):
    data = video_factories.make_video_bytes(duration_s=2.0, width=320, height=240)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    crop = VideoCropRect(x=0, y=0, width=240, height=240)
    output = VideoOutputSpec(resolution_width=120, resolution_height=120, quality="light")

    encoded = asyncio.run(transcode(path, crop, output, timeout_s=30))

    out_path = tmp_path / "out.mp4"
    out_path.write_bytes(encoded)
    info = asyncio.run(probe(out_path))
    assert info.width == 120
    assert info.height == 120


def test_transcode_without_crop_only_scales(tmp_path):
    data = video_factories.make_video_bytes(duration_s=1.0, width=320, height=240)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    output = VideoOutputSpec(resolution_width=160, resolution_height=120, quality="recommended")
    encoded = asyncio.run(transcode(path, None, output, timeout_s=30))

    out_path = tmp_path / "out.mp4"
    out_path.write_bytes(encoded)
    info = asyncio.run(probe(out_path))
    assert info.width == 160
    assert info.height == 120


def test_stronger_quality_preset_produces_a_smaller_file(tmp_path):
    data = video_factories.make_video_bytes(duration_s=2.0, width=320, height=240)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    same_size = VideoOutputSpec(resolution_width=320, resolution_height=240, quality="light")
    light = asyncio.run(transcode(path, None, same_size, timeout_s=30))

    same_size_strong = VideoOutputSpec(resolution_width=320, resolution_height=240, quality="strong")
    strong = asyncio.run(transcode(path, None, same_size_strong, timeout_s=30))

    assert len(strong) < len(light)


def test_transcode_webm_container_produces_playable_output(tmp_path):
    data = video_factories.make_video_bytes(duration_s=1.0, width=160, height=120)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    output = VideoOutputSpec(resolution_width=160, resolution_height=120, container="webm")
    encoded = asyncio.run(transcode(path, None, output, timeout_s=30))

    out_path = tmp_path / "out.webm"
    out_path.write_bytes(encoded)
    info = asyncio.run(probe(out_path))
    assert info.width == 160
    assert info.height == 120


def test_transcode_mkv_container_produces_playable_output(tmp_path):
    data = video_factories.make_video_bytes(duration_s=1.0, width=160, height=120)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    output = VideoOutputSpec(resolution_width=160, resolution_height=120, container="mkv")
    encoded = asyncio.run(transcode(path, None, output, timeout_s=30))

    out_path = tmp_path / "out.mkv"
    out_path.write_bytes(encoded)
    info = asyncio.run(probe(out_path))
    assert info.width == 160
    assert info.height == 120


def test_transcode_fps_30_changes_output_frame_rate(tmp_path):
    data = video_factories.make_video_bytes(duration_s=2.0, width=160, height=120, fps=15)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    output = VideoOutputSpec(resolution_width=160, resolution_height=120, fps=30)
    encoded = asyncio.run(transcode(path, None, output, timeout_s=30))

    out_path = tmp_path / "out.mp4"
    out_path.write_bytes(encoded)
    # A 2s clip re-timed to 30fps should have ~60 frames, not ~30 (source was 15fps).
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(out_path)],
        capture_output=True, text=True, check=True,
    )
    assert int(result.stdout.strip()) >= 55


def test_max_quality_produces_a_larger_file_than_light(tmp_path):
    data = video_factories.make_video_bytes(duration_s=2.0, width=320, height=240)
    path = tmp_path / "clip.mp4"
    path.write_bytes(data)

    light = asyncio.run(transcode(path, None, VideoOutputSpec(resolution_width=320, resolution_height=240, quality="light"), timeout_s=30))
    max_q = asyncio.run(transcode(path, None, VideoOutputSpec(resolution_width=320, resolution_height=240, quality="max"), timeout_s=30))

    assert len(max_q) > len(light)
