import pytest
from pydantic import ValidationError

from app.schemas.operations import MAX_DIMENSION
from app.schemas.pwa import PwaGenerateRequest


def _payload(**overrides):
    base = {
        "crop": {"x": 0, "y": 0, "width": 200, "height": 200},
        "background_color": "#FFFFFF",
        "manifest": {"name": "Mon App", "short_name": "MonApp", "theme_color": "#112233"},
    }
    base.update(overrides)
    return base


def test_valid_request_parses_with_default_platforms():
    request = PwaGenerateRequest.model_validate(_payload())
    assert request.platforms.android is True
    assert request.platforms.ios is True
    assert request.platforms.favicon is True
    assert request.platforms.windows is True
    assert request.platforms.splash is True
    assert request.manifest.display == "standalone"


def test_non_square_crop_is_rejected():
    with pytest.raises(ValidationError):
        PwaGenerateRequest.model_validate(_payload(crop={"x": 0, "y": 0, "width": 200, "height": 150}))


def test_invalid_hex_background_color_is_rejected():
    with pytest.raises(ValidationError):
        PwaGenerateRequest.model_validate(_payload(background_color="white"))


def test_short_name_over_twelve_chars_is_rejected():
    with pytest.raises(ValidationError):
        PwaGenerateRequest.model_validate(
            _payload(manifest={"name": "Mon App", "short_name": "NomBeaucoupTropLong", "theme_color": "#112233"})
        )


def test_oversized_crop_is_rejected_at_schema_layer():
    with pytest.raises(ValidationError):
        PwaGenerateRequest.model_validate(
            _payload(crop={"x": 0, "y": 0, "width": MAX_DIMENSION + 1, "height": MAX_DIMENSION + 1})
        )


def test_platforms_can_be_selectively_disabled():
    request = PwaGenerateRequest.model_validate(_payload(platforms={"windows": False, "splash": False}))
    assert request.platforms.windows is False
    assert request.platforms.splash is False
    assert request.platforms.android is True
