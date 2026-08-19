from app.schemas.request import OutputSpec

PRESETS: dict[str, dict[str, int]] = {
    "light": {"jpeg": 90, "webp": 88, "avif": 70, "png": 100},
    "recommended": {"jpeg": 80, "webp": 78, "avif": 55, "png": 100},
    "strong": {"jpeg": 65, "webp": 62, "avif": 42, "png": 100},
}

DEFAULT_PRESET = "recommended"


def resolve_quality(output: OutputSpec) -> int:
    """The numeric quality to encode at. Target-size mode uses this as its seed."""
    if output.quality is not None:
        return output.quality
    preset = output.preset or DEFAULT_PRESET
    return PRESETS[preset][output.format]
