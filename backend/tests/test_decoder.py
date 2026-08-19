import pytest

from app.engine.decoder import decode
from app.errors import ImageError
from tests import factories


def test_orientation_6_swaps_dimensions_and_clears_the_tag():
    # Orientation 6 means "rotate 90° CW to display". A 120x80 file must
    # come out 80x120 in pixels, with the tag neutralised so nothing
    # rotates it a second time.
    decoded = decode(factories.make_jpeg(size=(120, 80), orientation=6))

    assert decoded.image.size == (80, 120)
    assert decoded.image.getexif().get(factories.ORIENTATION, 1) == 1


@pytest.mark.parametrize("orientation", [1, 2, 3, 4, 5, 6, 7, 8])
def test_every_exif_orientation_decodes_to_upright_dimensions(orientation):
    decoded = decode(factories.make_jpeg(size=(120, 80), orientation=orientation))

    expected = (80, 120) if orientation in (5, 6, 7, 8) else (120, 80)
    assert decoded.image.size == expected


def test_icc_profile_is_captured():
    decoded = decode(factories.make_image_with_icc("JPEG"))
    assert decoded.icc_profile == factories.ICC_BYTES


def test_lying_extension_is_irrelevant_only_bytes_count():
    # decode() never sees a filename. Text that is not an image is rejected
    # on its header bytes alone.
    with pytest.raises(ImageError) as excinfo:
        decode(b"this is not an image, whatever it is named")
    assert excinfo.value.code == "UNSUPPORTED_FORMAT"


def test_truncated_file_is_reported_as_corrupt():
    with pytest.raises(ImageError) as excinfo:
        decode(factories.make_truncated_jpeg())
    assert excinfo.value.code == "CORRUPT_IMAGE"


def test_oversized_dimensions_are_refused_before_decoding(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_megapixels", 0.001)  # 1000 pixels
    with pytest.raises(ImageError) as excinfo:
        decode(factories.make_jpeg(size=(200, 200)))  # 40 000 pixels
    assert excinfo.value.code == "IMAGE_TOO_LARGE"


def test_a_header_declaring_a_giant_image_is_refused_with_our_error_code():
    # Pillow raises DecompressionBombError here, which is not an OSError.
    # It must still surface as our own IMAGE_TOO_LARGE, never as a crash.
    with pytest.raises(ImageError) as excinfo:
        decode(factories.make_png_bomb(20000, 20000))
    assert excinfo.value.code == "IMAGE_TOO_LARGE"
