"""Orchestrates one square source image into every enabled platform's PWA
asset set, plus manifest/snippet text files, zipped in-memory."""

import json
from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image

from app.engine.operations import crop as crop_op
from app.engine.pwa.ios_splash import IOS_SPLASH_SCREENS, SplashSpec
from app.engine.pwa.render import (
    _render_icon,
    _render_splash,
    browserconfig_xml,
    favicon_ico_bytes,
    manifest_dict,
    png_bytes,
    snippet_html,
)
from app.engine.pwa.specs import (
    ANDROID_ICONS,
    APPLE_ICONS,
    FAVICON_ICO_SIZES,
    FAVICON_PNG_SIZES,
    MASKABLE_ICONS,
    WINDOWS_TILE_SIZES,
    IconSpec,
)
from app.schemas.operations import CropOp
from app.schemas.pwa import PwaGenerateRequest


@dataclass
class GeneratedKit:
    zip_bytes: bytes
    file_count: int


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _crop_to_square(image: Image.Image, crop: CropOp) -> Image.Image:
    """Crop to the requested square region and normalise to RGBA so every
    downstream resize/paste operates on a single, predictable mode."""
    return crop_op.apply(image, crop).convert("RGBA")


def generate_kit(image: Image.Image, request: PwaGenerateRequest) -> GeneratedKit:
    square = _crop_to_square(image, CropOp(op="crop", **request.crop.model_dump()))
    background = _hex_to_rgb(request.background_color)

    files: dict[str, bytes] = {}
    icon_entries: list[dict] = []

    if request.platforms.android:
        for spec in (*ANDROID_ICONS, *MASKABLE_ICONS):
            files[spec.filename] = png_bytes(_render_icon(square, spec, background))
            icon_entries.append(
                {
                    "src": spec.filename,
                    "sizes": f"{spec.size}x{spec.size}",
                    "type": "image/png",
                    "purpose": spec.purpose,
                }
            )

    if request.platforms.ios:
        for spec in APPLE_ICONS:
            files[spec.filename] = png_bytes(_render_icon(square, spec, background))

    if request.platforms.favicon:
        for size in FAVICON_PNG_SIZES:
            spec = IconSpec(filename=f"favicon-{size}x{size}.png", size=size, purpose="any", opaque_background=False)
            files[spec.filename] = png_bytes(_render_icon(square, spec, background))
        files["favicon.ico"] = favicon_ico_bytes(square, FAVICON_ICO_SIZES)

    if request.platforms.windows:
        for size in WINDOWS_TILE_SIZES:
            spec = IconSpec(filename=f"windows/tile-{size}.png", size=size, purpose="any", opaque_background=True)
            files[spec.filename] = png_bytes(_render_icon(square, spec, background))
        files["windows/browserconfig.xml"] = browserconfig_xml(request.manifest.theme_color).encode("utf-8")

    splash_specs: tuple[SplashSpec, ...] = IOS_SPLASH_SCREENS if request.platforms.splash else ()
    for spec in splash_specs:
        files[spec.filename] = png_bytes(_render_splash(square, spec, background))

    files["manifest.webmanifest"] = json.dumps(manifest_dict(request, icon_entries), indent=2).encode("utf-8")
    files["snippet.html"] = snippet_html(
        request, request.platforms.ios, request.platforms.favicon, splash_specs
    ).encode("utf-8")

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)

    return GeneratedKit(zip_bytes=buffer.getvalue(), file_count=len(files))
