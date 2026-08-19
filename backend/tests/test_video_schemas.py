import pytest
from pydantic import ValidationError

from app.schemas.video import VideoCropRect, VideoOutputSpec, VideoProcessRequest


def test_crop_rect_rejects_negative_coordinates():
    with pytest.raises(ValidationError):
        VideoCropRect(x=-1, y=0, width=100, height=100)


def test_crop_rect_rejects_zero_or_negative_dimensions():
    with pytest.raises(ValidationError):
        VideoCropRect(x=0, y=0, width=0, height=100)


def test_output_spec_defaults_to_recommended_quality():
    spec = VideoOutputSpec(resolution_width=100, resolution_height=100)
    assert spec.quality == "recommended"


def test_output_spec_rejects_unknown_quality():
    with pytest.raises(ValidationError):
        VideoOutputSpec(resolution_width=100, resolution_height=100, quality="ultra")


def test_process_request_allows_no_crop():
    request = VideoProcessRequest(output=VideoOutputSpec(resolution_width=100, resolution_height=100))
    assert request.crop is None


def test_output_spec_defaults_to_mp4_and_original_fps():
    spec = VideoOutputSpec(resolution_width=100, resolution_height=100)
    assert spec.container == "mp4"
    assert spec.fps == "original"


def test_output_spec_accepts_max_quality_and_webm_and_60fps():
    spec = VideoOutputSpec(resolution_width=100, resolution_height=100, quality="max", container="webm", fps=60)
    assert spec.quality == "max"
    assert spec.container == "webm"
    assert spec.fps == 60
