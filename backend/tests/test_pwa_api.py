import json
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests import factories


@pytest.fixture
def client():
    return TestClient(app)


def _default_request(**overrides):
    payload = {
        "crop": {"x": 0, "y": 0, "width": 200, "height": 200},
        "background_color": "#FFFFFF",
        "manifest": {"name": "Mon App", "short_name": "MonApp", "theme_color": "#112233"},
    }
    payload.update(overrides)
    return payload


def _post(client, data: bytes, request: dict, filename: str = "logo.png"):
    return client.post(
        "/api/pwa/generate",
        files={"file": (filename, data, "application/octet-stream")},
        data={"request": json.dumps(request)},
    )


def test_generate_returns_a_zip_with_expected_files(client):
    source = factories.make_png_rgba((200, 200))

    response = _post(client, source, _default_request())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "pwa-assets.zip" in response.headers["content-disposition"]
    with ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        file_count = len(archive.namelist())
    assert "manifest.webmanifest" in names
    assert "icons/icon-192.png" in names
    assert "favicon.ico" in names
    assert int(response.headers["X-File-Count"]) == file_count


def test_platform_toggles_reduce_the_file_set(client):
    source = factories.make_png_rgba((200, 200))

    response = _post(
        client,
        source,
        _default_request(platforms={"android": True, "ios": False, "favicon": False, "windows": False, "splash": False}),
    )

    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
    assert "apple-touch-icon.png" not in names
    assert "favicon.ico" not in names
    assert not any(name.startswith("windows/") or name.startswith("splash/") for name in names)


def test_non_square_crop_is_refused(client):
    source = factories.make_photo((300, 300))

    response = _post(client, source, _default_request(crop={"x": 0, "y": 0, "width": 300, "height": 150}))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPERATION"


def test_invalid_background_color_is_refused(client):
    source = factories.make_photo((300, 300))

    response = _post(client, source, _default_request(background_color="not-a-color"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPERATION"


def test_a_non_image_upload_is_refused(client):
    response = _post(client, b"not an image", _default_request())

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"
