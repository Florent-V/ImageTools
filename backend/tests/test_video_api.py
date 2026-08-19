import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests import video_factories


@pytest.fixture
def client():
    return TestClient(app)


def test_inspect_video_returns_metadata_and_preview_frame(client):
    data = video_factories.make_video_bytes(duration_s=2.0, width=320, height=240)

    response = client.post("/api/video/inspect", files={"file": ("clip.mp4", data, "video/mp4")})

    assert response.status_code == 200
    body = response.json()
    assert body["width"] == 320
    assert body["height"] == 240
    assert body["preview_frame"].startswith("data:image/jpeg;base64,")


def test_inspect_video_rejects_non_video_files(client):
    data = video_factories.make_non_video_bytes()

    response = client.post("/api/video/inspect", files={"file": ("clip.mp4", data, "video/mp4")})

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_VIDEO_FORMAT"


def test_process_video_returns_mp4_and_size_headers(client):
    data = video_factories.make_video_bytes(duration_s=2.0, width=320, height=240)

    response = client.post(
        "/api/video/process",
        files={"file": ("clip.mp4", data, "video/mp4")},
        data={
            "request": json.dumps(
                {
                    "crop": {"x": 0, "y": 0, "width": 240, "height": 240},
                    "output": {"resolution_width": 120, "resolution_height": 120, "quality": "light"},
                }
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["X-Output-Width"] == "120"
    assert response.headers["X-Output-Height"] == "120"


def test_process_video_rejects_out_of_bounds_crop(client):
    data = video_factories.make_video_bytes(duration_s=1.0, width=320, height=240)

    response = client.post(
        "/api/video/process",
        files={"file": ("clip.mp4", data, "video/mp4")},
        data={
            "request": json.dumps(
                {
                    "crop": {"x": 0, "y": 0, "width": 999, "height": 999},
                    "output": {"resolution_width": 100, "resolution_height": 100},
                }
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPERATION"


def test_video_limits_endpoint(client):
    response = client.get("/api/video/limits")
    assert response.status_code == 200
    body = response.json()
    assert body["max_file_size_mb"] == 200
    assert body["max_duration_s"] == 60


def test_video_frame_endpoint_returns_preview_at_timestamp(client):
    data = video_factories.make_video_bytes(duration_s=3.0, width=160, height=120)

    response = client.post(
        "/api/video/frame",
        files={"file": ("clip.mp4", data, "video/mp4")},
        data={"timestamp_s": "1.5"},
    )

    assert response.status_code == 200
    assert response.json()["preview_frame"].startswith("data:image/jpeg;base64,")


def test_video_frame_endpoint_clamps_out_of_range_timestamp(client):
    data = video_factories.make_video_bytes(duration_s=1.0, width=160, height=120)

    response = client.post(
        "/api/video/frame",
        files={"file": ("clip.mp4", data, "video/mp4")},
        data={"timestamp_s": "999"},
    )

    assert response.status_code == 200
    assert response.json()["preview_frame"].startswith("data:image/jpeg;base64,")


def test_video_presets_endpoint(client):
    response = client.get("/api/video/presets")
    assert response.status_code == 200
    body = response.json()
    assert len(body["ratios"]) == 7
    assert "resolutions" not in body["ratios"][0]
    assert body["resolution_ladder"] == [
        {"label": "4K", "height": 2160}, {"label": "2K", "height": 1440},
        {"label": "1080p", "height": 1080}, {"label": "720p", "height": 720},
        {"label": "480p", "height": 480}, {"label": "360p", "height": 360},
    ]
    assert body["containers"] == [
        {"id": "mp4", "label": "MP4"}, {"id": "mov", "label": "MOV"},
        {"id": "mkv", "label": "MKV"}, {"id": "webm", "label": "WebM"},
    ]
    assert body["fps"] == ["original", 30, 60]
    assert body["quality"] == ["light", "recommended", "strong", "max"]
