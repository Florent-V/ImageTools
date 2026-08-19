from PIL import Image

from app.engine.encoder import encode

MAX_ATTEMPTS = 8


def encode_to_target(
    image: Image.Image,
    fmt: str,
    target_kb: int,
    icc_profile: bytes | None,
    exif: bytes | None,
) -> tuple[bytes, int]:
    """Binary-search the quality that lands just under target_kb.

    The image is already decoded, so each attempt costs only an encode.
    Returns the best result found, plus the quality that produced it.
    """
    target_bytes = target_kb * 1024
    low, high = 1, 100
    best: tuple[bytes, int] | None = None

    for _ in range(MAX_ATTEMPTS):
        if low > high:
            break
        quality = (low + high) // 2
        data = encode(image, fmt, quality, icc_profile, exif)

        if len(data) <= target_bytes:
            # Fits. Keep it and try harder for quality.
            if best is None or quality > best[1]:
                best = (data, quality)
            low = quality + 1
        else:
            high = quality - 1

    if best is not None:
        return best

    # Nothing fit. Hand back the smallest this format can produce.
    return encode(image, fmt, 1, icc_profile, exif), 1
