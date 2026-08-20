from PIL import Image

from app.config import settings
from app.errors import ImageError
from app.schemas.operations import ResizeOp

RESAMPLE = Image.Resampling.LANCZOS


def _target_size(current: tuple[int, int], op: ResizeOp) -> tuple[int, int]:
    # The final branch below dereferences op.height unconditionally. That is
    # safe because ResizeOp's check_dimensions validator rejects an operation
    # carrying none of percent, width or height — nothing without at least one
    # of them reaches this function.
    width, height = current

    if op.percent is not None:
        factor = op.percent / 100
        return max(1, round(width * factor)), max(1, round(height * factor))

    if not op.keep_ratio and op.width and op.height:
        return op.width, op.height

    if op.width and op.height:
        # Fit inside the box: the smaller factor wins, so nothing overflows.
        factor = min(op.width / width, op.height / height)
    elif op.width:
        factor = op.width / width
    else:
        factor = op.height / height

    return max(1, round(width * factor)), max(1, round(height * factor))


def apply(image: Image.Image, op: ResizeOp) -> Image.Image:
    target = _target_size(image.size, op)

    # Each dimension is bounded individually by the schema, but their product
    # isn't — a tiny source image can still request a huge output allocation.
    # Checked before no_upscale, which only skips the resize for the *source*
    # image's own size, not for an oversized explicit target.
    if target[0] * target[1] > settings.max_pixels:
        raise ImageError(
            "IMAGE_TOO_LARGE",
            f"Requested resize output exceeds the {settings.max_megapixels} megapixel limit",
            width=target[0],
            height=target[1],
        )

    if op.no_upscale and (target[0] > image.size[0] or target[1] > image.size[1]):
        return image
    if target == image.size:
        return image

    return image.resize(target, RESAMPLE)
