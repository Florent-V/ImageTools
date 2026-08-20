from PIL import Image

from app.errors import ImageError
from app.schemas.operations import CropOp


def validate_bounds(x: int, y: int, width: int, height: int, source_width: int, source_height: int) -> None:
    """Shared by the image op below and the video crop route — one rule, one place."""
    right = x + width
    bottom = y + height
    if right > source_width or bottom > source_height:
        raise ImageError(
            "INVALID_OPERATION",
            "The crop rectangle falls outside the source",
            source_width=source_width,
            source_height=source_height,
            requested_right=right,
            requested_bottom=bottom,
        )


def apply(image: Image.Image, op: CropOp) -> Image.Image:
    width, height = image.size
    validate_bounds(op.x, op.y, op.width, op.height, width, height)
    return image.crop((op.x, op.y, op.x + op.width, op.y + op.height))
