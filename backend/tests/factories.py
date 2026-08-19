"""Test images generated in code. Nothing is committed as a binary fixture."""

import os
import zlib
from io import BytesIO

import piexif
from PIL import Image, ImageCms

ICC_BYTES: bytes = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

GPS_LATITUDE_REF = 1
GPS_LATITUDE = 2
GPS_IFD = 0x8825
ORIENTATION = 0x0112


def make_bytes(fmt: str, size: tuple[int, int] = (120, 80), color=(200, 120, 40)) -> bytes:
    """A plain image in the given Pillow format name, no metadata."""
    image = Image.new("RGB", size, color)
    if fmt == "GIF":
        image = image.convert("P")  # GIF is palette-only
    buffer = BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


def make_jpeg(
    size: tuple[int, int] = (120, 80),
    orientation: int = 1,
    with_gps: bool = False,
) -> bytes:
    """A JPEG carrying an EXIF orientation tag and optionally GPS coordinates.

    Pillow's own Image.Exif() writer chokes on nested-tuple GPS rationals
    (TypeError in TiffImagePlugin's _limit_rational), so the GPS branch is
    built with piexif instead, which round-trips correctly through Pillow's
    reader (Image.getexif() / get_ifd()).
    """
    image = Image.new("RGB", size, (200, 120, 40))
    buffer = BytesIO()
    if with_gps:
        exif_dict = {
            "0th": {piexif.ImageIFD.Orientation: orientation},
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: "N",
                piexif.GPSIFD.GPSLatitude: ((48, 1), (51, 1), (2400, 100)),
            },
        }
        exif_bytes = piexif.dump(exif_dict)
        image.save(buffer, "JPEG", quality=95, exif=exif_bytes)
    else:
        exif = Image.Exif()
        exif[ORIENTATION] = orientation
        image.save(buffer, "JPEG", quality=95, exif=exif)
    return buffer.getvalue()


def make_png_rgba(size: tuple[int, int] = (120, 80)) -> bytes:
    """An RGBA PNG whose left half is fully transparent."""
    image = Image.new("RGBA", size, (0, 0, 255, 255))
    for x in range(size[0] // 2):
        for y in range(size[1]):
            image.putpixel((x, y), (0, 0, 255, 0))
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def make_image_with_icc(fmt: str = "JPEG", size: tuple[int, int] = (120, 80)) -> bytes:
    """An image carrying an embedded sRGB ICC profile."""
    image = Image.new("RGB", size, (10, 200, 90))
    buffer = BytesIO()
    image.save(buffer, fmt, icc_profile=ICC_BYTES)
    return buffer.getvalue()


def make_truncated_jpeg() -> bytes:
    """A JPEG with its second half cut off — header valid, pixel data broken."""
    data = make_jpeg(size=(400, 400))
    return data[: len(data) // 2]


def make_photo(size: tuple[int, int] = (400, 300)) -> bytes:
    """A gradient JPEG. Real detail, so compression settings actually move the size."""
    image = Image.new("RGB", size)
    for x in range(size[0]):
        for y in range(size[1]):
            image.putpixel((x, y), ((x * 7) % 256, (y * 11) % 256, ((x + y) * 3) % 256))
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=98)
    return buffer.getvalue()


def make_incompressible_photo(size: tuple[int, int] = (200, 200)) -> bytes:
    """Pure random pixel noise — the pathological case for DCT-based codecs.

    Real photos always compress well; this doesn't, which is the point: it
    reproduces libjpeg's optimize/progressive buffer-overrun failure at high
    quality (see encoder.py's encode() fallback).
    """
    image = Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3))
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def make_png_bomb(width: int, height: int) -> bytes:
    """A tiny PNG whose header declares enormous dimensions.

    Only the declared size is huge — the pixel data is a couple of bytes.
    That is the decompression-bomb shape: cheap to send, ruinous to decode.
    """
    patched = bytearray(make_bytes("PNG", size=(1, 1)))
    # PNG layout: 8-byte signature, then the IHDR chunk — length at 8-11,
    # type at 12-15, data at 16-28 (width and height first), CRC at 29-32.
    patched[16:20] = width.to_bytes(4, "big")
    patched[20:24] = height.to_bytes(4, "big")
    patched[29:33] = zlib.crc32(bytes(patched[12:29])).to_bytes(4, "big")
    return bytes(patched)


def make_cmyk_jpeg_with_icc(size: tuple[int, int] = (64, 48)) -> bytes:
    """A CMYK JPEG carrying a CMYK ICC profile — the print-workflow case."""
    image = Image.new("CMYK", size, (0, 0, 0, 0))
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    buffer = BytesIO()
    image.save(buffer, "JPEG", icc_profile=profile)
    return buffer.getvalue()


def make_palette_png_with_transparency(size: tuple[int, int] = (4, 2)) -> bytes:
    """An indexed PNG with a transparent palette entry.

    This is what a transparent GIF, or a PNG with a tRNS chunk, decodes to:
    mode "P" with no alpha band at all. The transparency lives in the file's
    metadata, not in the pixel bands.
    """
    image = Image.new("P", size, 1)
    image.putpalette([255, 0, 0, 0, 0, 255] + [0] * 760)
    buffer = BytesIO()
    image.save(buffer, "PNG", transparency=1)
    return buffer.getvalue()
