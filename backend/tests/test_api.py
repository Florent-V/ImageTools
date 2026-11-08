import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from tests import factories


@pytest.fixture
def client():
    return TestClient(app)


def _post(client, data: bytes, request: dict, filename: str = "photo.jpg"):
    return client.post(
        "/api/process",
        files={"file": (filename, data, "application/octet-stream")},
        data={"request": json.dumps(request)},
    )


def test_process_returns_the_image_and_size_headers(client):
    source = factories.make_photo((400, 300))

    response = _post(
        client,
        source,
        {"ops": [{"op": "resize", "width": 200}], "output": {"format": "webp"}},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["X-Output-Width"] == "200"
    assert response.headers["X-Output-Height"] == "150"
    assert response.headers["X-Input-Size"] == str(len(source))
    assert Image.open(BytesIO(response.content)).size == (200, 150)


def test_a_lying_filename_does_not_change_the_verdict(client):
    # The bytes are a PNG; the name claims JPEG. The name is ignored.
    response = _post(
        client, factories.make_bytes("PNG"), {"output": {"format": "jpeg"}}, "evil.jpg"
    )

    assert response.status_code == 200
    assert Image.open(BytesIO(response.content)).format == "JPEG"


def test_a_non_image_upload_is_refused(client):
    response = _post(client, b"#!/bin/sh\nrm -rf /", {"output": {"format": "png"}})

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_an_out_of_bounds_crop_is_refused(client):
    response = _post(
        client,
        factories.make_jpeg(size=(100, 100)),
        {"ops": [{"op": "crop", "x": 90, "y": 0, "width": 50, "height": 50}],
         "output": {"format": "png"}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPERATION"


def test_malformed_request_json_is_refused(client):
    response = client.post(
        "/api/process",
        files={"file": ("a.jpg", factories.make_jpeg(), "image/jpeg")},
        data={"request": "{not json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPERATION"


def test_formats_endpoint_lists_what_the_engine_supports(client):
    body = client.get("/api/formats").json()

    assert set(body["write"]) == {"jpeg", "png", "webp", "avif"}
    assert "JPEG" in body["read"]
    assert body["presets"]["recommended"]["avif"] == 55


def test_inspect_reports_dimensions_and_flags_gps(client):
    response = client.post(
        "/api/inspect",
        files={"file": ("a.jpg", factories.make_jpeg(with_gps=True), "image/jpeg")},
    )

    body = response.json()
    assert body["width"] == 120
    assert body["format"] == "JPEG"
    assert body["has_gps"] is True


def test_inspect_refuses_a_declared_size_bomb(client):
    # A header declaring a giant image must be refused with our own code,
    # not crash into a generic 500. Same guard the decoder already applies
    # on /process — /inspect must not be the soft underbelly.
    response = client.post(
        "/api/inspect",
        files={"file": ("huge.png", factories.make_png_bomb(20000, 20000), "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_logs_never_carry_the_client_filename(client, caplog):
    # The privacy promise: the server records the shape of the work, never
    # anything identifying. A distinctive filename must not appear in any log.
    import logging

    marker = "my-private-vacation-photo-at-home.jpg"
    with caplog.at_level(logging.INFO):
        client.post(
            "/api/process",
            files={"file": (marker, factories.make_photo(), "image/jpeg")},
            data={"request": '{"ops": [], "output": {"format": "webp"}}'},
        )

    assert marker not in caplog.text


def test_a_processing_timeout_is_reported_within_the_error_contract(client, monkeypatch):
    # Force the work to outlast a tiny timeout; the response must be our own
    # error code, not a hung request or a raw 500.
    import time

    from app.api import routes
    from app.config import settings

    monkeypatch.setattr(settings, "request_timeout_s", 0.05)
    monkeypatch.setattr(routes, "process", lambda data, req, watermark_data=None: time.sleep(1))

    response = client.post(
        "/api/process",
        files={"file": ("a.jpg", factories.make_jpeg(), "image/jpeg")},
        data={"request": '{"ops": [], "output": {"format": "png"}}'},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "PROCESSING_FAILED"
