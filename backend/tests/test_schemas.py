import pytest
from pydantic import ValidationError

from app.engine.presets import resolve_quality
from app.schemas.request import OutputSpec, ProcessRequest


def test_resize_rejects_no_dimension_at_all():
    with pytest.raises(ValidationError):
        ProcessRequest.model_validate(
            {"ops": [{"op": "resize"}], "output": {"format": "webp"}}
        )


def test_output_rejects_two_quality_modes_at_once():
    with pytest.raises(ValidationError):
        OutputSpec.model_validate({"format": "jpeg", "quality": 80, "target_size_kb": 500})


def test_output_defaults_to_recommended_preset():
    assert resolve_quality(OutputSpec.model_validate({"format": "avif"})) == 55


def test_explicit_quality_wins_over_preset_table():
    assert resolve_quality(OutputSpec.model_validate({"format": "jpeg", "quality": 42})) == 42


def test_unknown_operation_is_rejected():
    with pytest.raises(ValidationError):
        ProcessRequest.model_validate(
            {"ops": [{"op": "sharpen"}], "output": {"format": "png"}}
        )
