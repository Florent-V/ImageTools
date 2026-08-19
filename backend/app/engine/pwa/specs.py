"""Per-platform PWA icon spec tables. Stable, rarely-changing web-platform
constants — kept separate from `ios_splash.py`, which is the one table
expected to need updates as Apple ships new device screen sizes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IconSpec:
    filename: str
    size: int
    purpose: str  # "any" or "maskable" — the manifest.webmanifest icon `purpose` value
    opaque_background: bool
    safe_zone_scale: float = 1.0  # fraction of the canvas the icon content occupies


ANDROID_ICON_SIZES: tuple[int, ...] = (48, 72, 96, 128, 144, 152, 192, 384, 512)
ANDROID_ICONS: tuple[IconSpec, ...] = tuple(
    IconSpec(filename=f"icons/icon-{size}.png", size=size, purpose="any", opaque_background=False)
    for size in ANDROID_ICON_SIZES
)

MASKABLE_ICON_SIZES: tuple[int, ...] = (192, 512)
# 0.8 keeps icon content inside the 80% "safe zone" every maskable-icon
# consumer (Android adaptive icons, etc.) is expected to honour — content
# outside it risks being clipped by the OS's mask shape.
MASKABLE_ICONS: tuple[IconSpec, ...] = tuple(
    IconSpec(
        filename=f"icons/maskable-{size}.png",
        size=size,
        purpose="maskable",
        opaque_background=True,
        safe_zone_scale=0.8,
    )
    for size in MASKABLE_ICON_SIZES
)

APPLE_ICON_SIZES: tuple[int, ...] = (120, 152, 167, 180)
APPLE_ICONS: tuple[IconSpec, ...] = tuple(
    IconSpec(filename=f"icons/apple-touch-icon-{size}.png", size=size, purpose="any", opaque_background=True)
    for size in APPLE_ICON_SIZES
) + (
    # iOS/Safari looks for this exact size-less filename by default.
    IconSpec(filename="apple-touch-icon.png", size=180, purpose="any", opaque_background=True),
)

FAVICON_PNG_SIZES: tuple[int, ...] = (16, 32)
FAVICON_ICO_SIZES: tuple[int, ...] = (16, 32, 48)

WINDOWS_TILE_SIZES: tuple[int, ...] = (70, 150, 310)
