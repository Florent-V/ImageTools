from dataclasses import dataclass

from app.engine.decoder import decode
from app.engine.encoder import encode
from app.engine.operations.registry import apply_operations
from app.engine.presets import resolve_quality
from app.engine.target_size import encode_to_target
from app.schemas.request import ProcessRequest


@dataclass
class ProcessResult:
    data: bytes
    width: int
    height: int
    output_size: int
    input_size: int
    format: str
    quality: int


def process(data: bytes, request: ProcessRequest, watermark_data: bytes | None = None) -> ProcessResult:
    """Decode once, apply the operations in order, encode once."""
    decoded = decode(data)
    image = apply_operations(decoded.image, request.ops, watermark_data)

    exif = None if request.output.strip_metadata else decoded.exif
    fmt = request.output.format

    if request.output.target_size_kb is not None:
        encoded, quality = encode_to_target(
            image, fmt, request.output.target_size_kb, decoded.icc_profile, exif
        )
    else:
        quality = resolve_quality(request.output)
        encoded = encode(image, fmt, quality, decoded.icc_profile, exif)

    return ProcessResult(
        data=encoded,
        width=image.width,
        height=image.height,
        output_size=len(encoded),
        input_size=decoded.input_size,
        format=fmt,
        quality=quality,
    )
