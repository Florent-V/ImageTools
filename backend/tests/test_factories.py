from io import BytesIO

from PIL import Image

from tests import factories


def test_factory_writes_gps_and_orientation():
    data = factories.make_jpeg(orientation=6, with_gps=True)
    exif = Image.open(BytesIO(data)).getexif()

    assert exif[factories.ORIENTATION] == 6
    gps = exif.get_ifd(factories.GPS_IFD)
    assert gps[factories.GPS_LATITUDE_REF] == "N"


def test_factory_embeds_icc_profile():
    data = factories.make_image_with_icc("JPEG")
    assert Image.open(BytesIO(data)).info.get("icc_profile") == factories.ICC_BYTES


def test_factory_writes_every_read_format():
    for fmt in ("JPEG", "PNG", "WEBP", "AVIF", "GIF", "TIFF", "BMP"):
        image = Image.open(BytesIO(factories.make_bytes(fmt)))
        assert image.format == fmt
