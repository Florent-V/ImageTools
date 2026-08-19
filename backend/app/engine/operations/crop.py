from PIL import Image

from app.errors import ImageError
from app.schemas.operations import CropOp


def apply(image: Image.Image, op: CropOp) -> Image.Image:
    width, height = image.size
    right = op.x + op.width
    bottom = op.y + op.height

    if right > width or bottom > height:
        raise ImageError(
            "INVALID_OPERATION",
            "The crop rectangle falls outside the image",
            image_width=width,
            image_height=height,
            requested_right=right,
            requested_bottom=bottom,
        )

    return image.crop((op.x, op.y, right, bottom))
