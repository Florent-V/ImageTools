from io import BytesIO

from PIL import Image

from app.engine.decoder import decode
from app.engine.encoder import encode
from tests import factories


def test_icc_profile_survives_even_when_metadata_is_stripped():
    decoded = decode(factories.make_image_with_icc("JPEG"))

    data = encode(decoded.image, "jpeg", 85, decoded.icc_profile, exif=None)

    assert Image.open(BytesIO(data)).info.get("icc_profile") == factories.ICC_BYTES


def test_gps_is_really_gone_when_exif_is_dropped():
    # Read the encoded bytes back rather than trusting the call succeeded.
    decoded = decode(factories.make_jpeg(with_gps=True))

    data = encode(decoded.image, "jpeg", 85, decoded.icc_profile, exif=None)

    exif = Image.open(BytesIO(data)).getexif()
    assert exif.get_ifd(factories.GPS_IFD) == {}


def test_gps_is_kept_when_exif_is_passed_through():
    decoded = decode(factories.make_jpeg(with_gps=True))

    data = encode(decoded.image, "jpeg", 85, decoded.icc_profile, decoded.exif)

    gps = Image.open(BytesIO(data)).getexif().get_ifd(factories.GPS_IFD)
    assert gps[factories.GPS_LATITUDE_REF] == "N"


def test_transparent_png_flattens_onto_white_for_jpeg():
    # JPEG has no alpha channel. Without flattening, Pillow raises.
    decoded = decode(factories.make_png_rgba())

    data = encode(decoded.image, "jpeg", 85, None, None)

    result = Image.open(BytesIO(data))
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (255, 255, 255)


def test_transparency_is_preserved_for_webp():
    decoded = decode(factories.make_png_rgba())

    data = encode(decoded.image, "webp", 85, None, None)

    assert Image.open(BytesIO(data)).mode == "RGBA"


def test_palette_transparency_survives_into_webp():
    # Mode "P" has no alpha band, so a bands-based check misses it and the
    # image silently flattens. The transparency is in the file metadata.
    decoded = decode(factories.make_palette_png_with_transparency())

    data = encode(decoded.image, "webp", 90, None, None)

    assert Image.open(BytesIO(data)).mode == "RGBA"


def test_lower_quality_produces_a_smaller_file():
    decoded = decode(factories.make_photo())

    big = encode(decoded.image, "jpeg", 95, None, None)
    small = encode(decoded.image, "jpeg", 40, None, None)

    assert len(small) < len(big)


def test_cmyk_icc_is_dropped_when_converting_to_rgb_jpeg():
    # The captured profile is CMYK; the output pixels are RGB. Re-attaching
    # the CMYK profile would make a colour-managed viewer mis-render. It must
    # be dropped, not preserved onto the wrong colour model.
    decoded = decode(factories.make_cmyk_jpeg_with_icc())
    assert decoded.icc_profile is not None  # the profile was captured

    data = encode(decoded.image, "jpeg", 85, decoded.icc_profile, exif=None)

    out = Image.open(BytesIO(data))
    assert out.mode == "RGB"
    assert out.info.get("icc_profile") is None


def test_pathological_content_still_encodes_at_max_quality():
    # Random noise defeats libjpeg's optimize/progressive buffer sizing
    # (Pillow guesses 2x the raw pixel count), aborting the write mid-stream.
    # encode() must fall back to a plain baseline encode rather than 500.
    decoded = decode(factories.make_incompressible_photo())

    data = encode(decoded.image, "jpeg", 100, None, None)

    result = Image.open(BytesIO(data))
    assert result.size == (200, 200)


def test_rgb_icc_still_survives_the_alpha_flatten_to_jpeg():
    # RGBA flattening to RGB is NOT a colour-model change, so an RGB profile
    # must still be preserved — Fix 1 must not over-reach.
    decoded = decode(factories.make_image_with_icc("JPEG"))

    data = encode(decoded.image, "jpeg", 85, decoded.icc_profile, exif=None)

    assert Image.open(BytesIO(data)).info.get("icc_profile") == factories.ICC_BYTES
