from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

from app.config import settings
from app.errors import ImageError

# Security-critical and process-global: a truncated file must be an error,
# never a silently half-decoded image. Pillow's default is False; pin it so
# no future import can flip it underneath us.
ImageFile.LOAD_TRUNCATED_IMAGES = False

READ_FORMATS: frozenset[str] = frozenset(
    {"JPEG", "PNG", "WEBP", "AVIF", "GIF", "TIFF", "BMP"}
)


@dataclass
class Decoded:
    image: Image.Image
    icc_profile: bytes | None
    exif: bytes | None
    source_format: str
    input_size: int


def decode(data: bytes) -> Decoded:
    """Validate, decode, and normalise orientation.

    Nothing here trusts a filename or a declared content type: the format
    comes from the header bytes Pillow sniffs.
    """
    if len(data) > settings.max_file_size_bytes:
        raise ImageError(
            "FILE_TOO_LARGE",
            f"File exceeds the {settings.max_file_size_mb} MB limit",
            limit_bytes=settings.max_file_size_bytes,
        )

    try:
        image = Image.open(BytesIO(data))
    except Image.DecompressionBombError:
        raise ImageError(
            "IMAGE_TOO_LARGE",
            "The image header declares implausibly large dimensions",
        )
    except UnidentifiedImageError:
        raise ImageError("UNSUPPORTED_FORMAT", "Unrecognised image format")
    except OSError:
        raise ImageError("CORRUPT_IMAGE", "The file could not be read as an image")

    if image.format not in READ_FORMATS:
        raise ImageError(
            "UNSUPPORTED_FORMAT",
            f"{image.format} files cannot be read",
            format=image.format,
        )

    # Image.open is lazy — size is known before any pixel is decoded, which
    # is what makes this check a defence against decompression bombs.
    width, height = image.size
    if width * height > settings.max_pixels:
        raise ImageError(
            "IMAGE_TOO_LARGE",
            f"Image exceeds the {settings.max_megapixels} megapixel limit",
            width=width,
            height=height,
        )

    icc_profile = image.info.get("icc_profile")
    source_format = image.format

    try:
        image.load()
        # Bakes the EXIF orientation into the pixels and removes the tag, so
        # a later crop operates on the coordinates the user actually saw.
        image = ImageOps.exif_transpose(image)
    except OSError:
        raise ImageError("CORRUPT_IMAGE", "The image data is truncated or damaged")

    exif_bytes = image.getexif().tobytes() if image.getexif() else None

    return Decoded(
        image=image,
        icc_profile=icc_profile,
        exif=exif_bytes,
        source_format=source_format,
        input_size=len(data),
    )
