"""Rendering primitives shared by every platform's icon/splash generation,
plus the manifest / HTML snippet / browserconfig text builders."""

import html
from io import BytesIO

from PIL import Image

from app.engine.pwa.ios_splash import SplashSpec
from app.engine.pwa.specs import IconSpec
from app.schemas.pwa import PwaGenerateRequest

RESAMPLE = Image.Resampling.LANCZOS


def _render_icon(source: Image.Image, spec: IconSpec, background: tuple[int, int, int]) -> Image.Image:
    """`source` must already be RGBA. Resize onto a canvas sized/composited per `spec`."""
    content_size = max(1, round(spec.size * spec.safe_zone_scale))
    resized = source.resize((content_size, content_size), RESAMPLE)
    offset = (spec.size - content_size) // 2

    if not spec.opaque_background:
        if content_size == spec.size:
            return resized
        canvas = Image.new("RGBA", (spec.size, spec.size), (0, 0, 0, 0))
        canvas.paste(resized, (offset, offset), resized)
        return canvas

    canvas = Image.new("RGB", (spec.size, spec.size), background)
    canvas.paste(resized, (offset, offset), resized)
    return canvas


def _render_splash(source: Image.Image, spec: SplashSpec, background: tuple[int, int, int]) -> Image.Image:
    """Center the icon at ~40% of the shortest screen side on a bg-color canvas."""
    canvas = Image.new("RGB", (spec.width, spec.height), background)
    icon_size = round(min(spec.width, spec.height) * 0.4)
    resized = source.resize((icon_size, icon_size), RESAMPLE)
    offset = ((spec.width - icon_size) // 2, (spec.height - icon_size) // 2)
    canvas.paste(resized, offset, resized)
    return canvas


def png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, "PNG", optimize=True, compress_level=9)
    return buffer.getvalue()


def favicon_ico_bytes(source: Image.Image, sizes: tuple[int, ...]) -> bytes:
    buffer = BytesIO()
    source.save(buffer, "ICO", sizes=[(s, s) for s in sizes])
    return buffer.getvalue()


def browserconfig_xml(tile_color: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<browserconfig>\n"
        "  <msapplication>\n"
        "    <tile>\n"
        '      <square70x70logo src="tile-70.png"/>\n'
        '      <square150x150logo src="tile-150.png"/>\n'
        '      <square310x310logo src="tile-310.png"/>\n'
        f"      <TileColor>{tile_color}</TileColor>\n"
        "    </tile>\n"
        "  </msapplication>\n"
        "</browserconfig>\n"
    )


def manifest_dict(request: PwaGenerateRequest, icon_entries: list[dict]) -> dict:
    manifest = {
        "name": request.manifest.name,
        "short_name": request.manifest.short_name,
        "start_url": "/",
        "display": request.manifest.display,
        "background_color": request.background_color,
        "theme_color": request.manifest.theme_color,
        "icons": icon_entries,
    }
    if request.manifest.description:
        manifest["description"] = request.manifest.description
    if request.manifest.orientation:
        manifest["orientation"] = request.manifest.orientation
    return manifest


def snippet_html(
    request: PwaGenerateRequest,
    apple_generated: bool,
    favicon_generated: bool,
    splash_specs: tuple[SplashSpec, ...],
) -> str:
    lines = [
        '<link rel="manifest" href="manifest.webmanifest">',
        f'<meta name="theme-color" content="{request.manifest.theme_color}">',
    ]
    if favicon_generated:
        lines += [
            '<link rel="icon" href="favicon.ico" sizes="any">',
            '<link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">',
            '<link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">',
        ]
    if apple_generated:
        lines += [
            '<link rel="apple-touch-icon" href="apple-touch-icon.png">',
            '<meta name="apple-mobile-web-app-capable" content="yes">',
            f'<meta name="apple-mobile-web-app-title" content="{html.escape(request.manifest.short_name, quote=True)}">',
        ]
    for spec in splash_specs:
        lines.append(f'<link rel="apple-touch-startup-image" href="{spec.filename}" media="{spec.media}">')
    if request.platforms.windows:
        lines += [
            f'<meta name="msapplication-TileColor" content="{request.manifest.theme_color}">',
            '<meta name="msapplication-config" content="windows/browserconfig.xml">',
        ]
    return "\n".join(lines) + "\n"
