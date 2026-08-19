from collections.abc import Callable

from PIL import Image

from app.engine.operations import crop, resize, rotate, watermark
from app.schemas.operations import Operation

# Adding an operation means adding a module and one line here.
OPERATIONS: dict[str, Callable] = {
    "resize": resize.apply,
    "crop": crop.apply,
    "rotate": rotate.apply,
}


def apply_operations(
    image: Image.Image, ops: list[Operation], watermark_data: bytes | None = None
) -> Image.Image:
    """Apply operations in array order. The order is the contract — never sorted."""
    for op in ops:
        if op.op == "watermark":
            image = watermark.apply(image, op, watermark_data)
        else:
            image = OPERATIONS[op.op](image, op)
    return image
