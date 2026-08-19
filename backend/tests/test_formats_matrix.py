from io import BytesIO

import pytest
from PIL import Image

from app.engine.pipeline import process
from app.schemas.request import ProcessRequest
from tests import factories

READ = ["JPEG", "PNG", "WEBP", "AVIF", "GIF", "TIFF", "BMP"]
WRITE = ["jpeg", "png", "webp", "avif"]


@pytest.mark.parametrize("source", READ)
@pytest.mark.parametrize("target", WRITE)
def test_every_input_format_converts_to_every_output_format(source, target):
    request = ProcessRequest.model_validate({"ops": [], "output": {"format": target}})

    result = process(factories.make_bytes(source, size=(60, 40)), request)

    produced = Image.open(BytesIO(result.data))
    assert produced.format == target.upper()
    assert produced.size == (60, 40)
    assert result.width == 60 and result.height == 40


def test_a_full_chain_reports_the_final_dimensions():
    request = ProcessRequest.model_validate(
        {
            "ops": [
                {"op": "resize", "width": 200, "height": 150, "keep_ratio": False},
                {"op": "crop", "x": 0, "y": 0, "width": 100, "height": 100},
                {"op": "rotate", "degrees": 90},
            ],
            "output": {"format": "webp", "preset": "strong"},
        }
    )

    result = process(factories.make_photo((400, 300)), request)

    assert (result.width, result.height) == (100, 100)
    assert result.quality == 62
