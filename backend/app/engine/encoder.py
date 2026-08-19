from io import BytesIO

from PIL import Image

from app.errors import ImageError

PILLOW_FORMAT: dict[str, str] = {
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "avif": "AVIF",
}

MEDIA_TYPE: dict[str, str] = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "avif": "image/avif",
}

FILE_EXTENSION: dict[str, str] = {
    "jpeg": "jpg",
    "png": "png",
    "webp": "webp",
    "avif": "avif",
}


def _color_family(mode: str) -> str:
    """The colour model an ICC profile would describe for this Pillow mode.

    Palette images are RGB-backed, so P/PA count as rgb. An ICC profile stays
    valid only while the family is unchanged; converting CMYK or grayscale to
    RGB invalidates it.
    """
    if mode in ("RGB", "RGBA", "P", "PA"):
        return "rgb"
    if mode in ("L", "LA", "1", "I", "I;16", "F"):
        return "gray"
    if mode == "CMYK":
        return "cmyk"
    return mode


def _prepare_mode(image: Image.Image, fmt: str) -> Image.Image:
    if fmt == "jpeg":
        if image.mode in ("RGBA", "LA", "P", "PA"):
            rgba = image.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, (255, 255, 255))
            flattened.paste(rgba, mask=rgba.split()[-1])
            return flattened
        return image if image.mode == "RGB" else image.convert("RGB")

    if fmt in ("webp", "avif"):
        if image.mode in ("RGB", "RGBA"):
            return image
        # A palette image carries its transparency in info, not in a band,
        # so getbands() alone would flatten a transparent GIF or indexed PNG.
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        return image.convert("RGBA" if has_alpha else "RGB")

    return image  # PNG handles every mode we can produce


def _save_options(fmt: str, quality: int) -> dict:
    if fmt == "jpeg":
        options = {"quality": quality, "optimize": True, "progressive": True}
        if quality > 90:
            # 4:4:4 — above this quality, chroma subsampling smears flat colour.
            options["subsampling"] = 0
        return options

    if fmt == "png":
        return {"optimize": True, "compress_level": 9}

    if fmt == "webp":
        return {"lossless": True} if quality == 100 else {"quality": quality, "method": 4}

    return {"quality": quality}  # avif


def encode(
    image: Image.Image,
    fmt: str,
    quality: int,
    icc_profile: bytes | None,
    exif: bytes | None,
) -> bytes:
    """Encode to bytes. The ICC profile always rides along; EXIF only if given."""
    prepared = _prepare_mode(image, fmt)
    options = _save_options(fmt, quality)

    keep_icc = icc_profile and _color_family(image.mode) == _color_family(prepared.mode)
    if keep_icc:
        options["icc_profile"] = icc_profile
    if exif:
        options["exif"] = exif

    buffer = BytesIO()
    try:
        prepared.save(buffer, PILLOW_FORMAT[fmt], **options)
    except OSError as exc:
        if options.get("optimize") or options.get("progressive"):
            # libjpeg's optimize/progressive path needs the whole encoded
            # image in one buffer; Pillow sizes it at 2x the raw pixel count,
            # which near-incompressible content (e.g. dense noise) can still
            # exceed, aborting the write mid-stream. Retry once without
            # optimize/progressive — a plain baseline encode always fits.
            fallback = {k: v for k, v in options.items() if k not in ("optimize", "progressive")}
            buffer = BytesIO()
            try:
                prepared.save(buffer, PILLOW_FORMAT[fmt], **fallback)
            except (OSError, ValueError) as retry_exc:
                raise ImageError("PROCESSING_FAILED", f"Encoding to {fmt} failed: {retry_exc}")
        else:
            raise ImageError("PROCESSING_FAILED", f"Encoding to {fmt} failed: {exc}")
    except ValueError as exc:
        raise ImageError("PROCESSING_FAILED", f"Encoding to {fmt} failed: {exc}")

    return buffer.getvalue()
