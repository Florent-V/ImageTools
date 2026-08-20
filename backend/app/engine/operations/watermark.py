from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from app.engine.decoder import check_pixel_limit
from app.errors import ImageError
from app.schemas.operations import WatermarkOp

# Sampled at this size, then linearly rescaled to hit the target pixel width —
# avoids a search loop for what is a decorative overlay, not typography.
_SAMPLE_FONT_SIZE = 40

# A narrow sample glyph (e.g. a single "." or "'") gives a tiny sample_width,
# which without a ceiling drives the rescaled size into the tens of
# thousands — an unbounded Pillow glyph-raster allocation. No legitimate
# watermark needs a font taller than this.
_MAX_FONT_SIZE = 2000


def _fit_font_to_width(text: str, target_width: float) -> ImageFont.FreeTypeFont:
    sample = ImageFont.load_default(size=_SAMPLE_FONT_SIZE)
    bbox = sample.getbbox(text)
    sample_width = bbox[2] - bbox[0]
    if sample_width <= 0:
        return sample
    size = round(_SAMPLE_FONT_SIZE * target_width / sample_width)
    size = max(8, min(_MAX_FONT_SIZE, size))
    return ImageFont.load_default(size=size)


def _build_image_tile(base_width: int, op: WatermarkOp, watermark_data: bytes | None) -> Image.Image:
    if watermark_data is None:
        raise ImageError("INVALID_OPERATION", "Image watermark requires a watermark file")
    try:
        mark = Image.open(BytesIO(watermark_data))
    except Image.DecompressionBombError:
        raise ImageError("IMAGE_TOO_LARGE", "The watermark image header declares implausibly large dimensions")
    except (UnidentifiedImageError, OSError):
        raise ImageError("UNSUPPORTED_FORMAT", "Unrecognised watermark image format")

    # Image.open is lazy — same bomb defence as the main decode path, applied
    # here too since this file bypasses app.engine.decoder.decode().
    check_pixel_limit(mark.width, mark.height)
    mark = mark.convert("RGBA")

    target_width = max(1, round(base_width * op.scale))
    target_height = max(1, round(mark.height * target_width / mark.width))
    return mark.resize((target_width, target_height), Image.LANCZOS)


def _build_text_tile(base_width: int, op: WatermarkOp) -> Image.Image:
    text = op.text or ""
    font = _fit_font_to_width(text, base_width * op.scale)
    bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font)
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])

    tile = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((-bbox[0], -bbox[1]), text, font=font, fill=(0, 0, 0, 255))
    return tile


def apply(image: Image.Image, op: WatermarkOp, watermark_data: bytes | None = None) -> Image.Image:
    base = image.convert("RGBA")
    result = base

    # The veil is a wash over the whole photo, independent of the watermark
    # itself — always composited first so the watermark stays on top of it.
    if op.white_veil:
        veil = Image.new("RGBA", base.size, (255, 255, 255, round(255 * op.veil_opacity)))
        result = Image.alpha_composite(result, veil)

    tile = _build_image_tile(base.width, op, watermark_data) if op.mode == "image" else _build_text_tile(base.width, op)

    # Scale alpha directly on the tile (straight, non-premultiplied colour)
    # rather than via Image.paste(..., mask=tile): pasting a partially
    # transparent image as its own mask blends the RGB toward black in
    # proportion to alpha too, silently darkening the watermark as opacity
    # drops instead of just fading it.
    alpha = tile.getchannel("A").point(lambda a: round(a * op.opacity))
    tile.putalpha(alpha)

    if op.rotation:
        tile = tile.rotate(op.rotation, expand=True, resample=Image.BICUBIC)

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    x = round(op.position_x * base.width - tile.width / 2)
    y = round(op.position_y * base.height - tile.height / 2)
    layer.paste(tile, (x, y))

    result = Image.alpha_composite(result, layer)
    return result if "A" in image.getbands() else result.convert("RGB")
