from PIL import Image

from app.schemas.operations import RotateOp

# Pillow's transpose constants rotate counter-clockwise; the API speaks
# clockwise, which is what every photo tool means by "rotate 90".
_CLOCKWISE = {
    90: Image.Transpose.ROTATE_270,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_90,
}


def apply(image: Image.Image, op: RotateOp) -> Image.Image:
    if op.degrees:
        image = image.transpose(_CLOCKWISE[op.degrees])
    if op.flip_horizontal:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if op.flip_vertical:
        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return image
