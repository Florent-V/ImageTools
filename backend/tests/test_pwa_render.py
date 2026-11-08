import json
from io import BytesIO

from PIL import Image

from app.engine.pwa.ios_splash import SplashSpec
from app.engine.pwa.render import (
    _render_icon,
    _render_splash,
    browserconfig_xml,
    favicon_ico_bytes,
    manifest_dict,
    png_bytes,
    snippet_html,
)
from app.engine.pwa.specs import IconSpec
from app.schemas.pwa import PwaGenerateRequest


def _request(**platform_overrides):
    payload = {
        "crop": {"x": 0, "y": 0, "width": 200, "height": 200},
        "background_color": "#112233",
        "manifest": {"name": "Mon App", "short_name": "MonApp", "theme_color": "#445566"},
        "platforms": {
            "android": True,
            "ios": True,
            "favicon": True,
            "windows": True,
            "splash": True,
            **platform_overrides,
        },
    }
    return PwaGenerateRequest.model_validate(payload)


def _rgba_square(size: int = 200) -> Image.Image:
    return Image.new("RGBA", (size, size), (10, 20, 30, 255))


def _rgba_square_with_transparent_border(size: int = 200, border: int = 20) -> Image.Image:
    """Opaque center, fully transparent border — lets flattening-onto-background be observed."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = Image.new("RGBA", (size - 2 * border, size - 2 * border), (10, 20, 30, 255))
    image.paste(inner, (border, border))
    return image


def test_render_icon_non_opaque_preserves_alpha_and_fills_the_canvas():
    source = _rgba_square()
    spec = IconSpec(filename="icons/icon-96.png", size=96, purpose="any", opaque_background=False)
    result = _render_icon(source, spec, (255, 255, 255))
    assert result.size == (96, 96)
    assert result.mode == "RGBA"


def test_render_icon_opaque_flattens_onto_background_color():
    source = _rgba_square_with_transparent_border()
    spec = IconSpec(filename="icons/apple-touch-icon-180.png", size=180, purpose="any", opaque_background=True)
    result = _render_icon(source, spec, (255, 0, 0))
    assert result.size == (180, 180)
    assert result.mode == "RGB"
    # Corner falls in the source's transparent border — must show background, never source content.
    assert result.getpixel((0, 0)) == (255, 0, 0)
    # Center falls in the source's opaque region — must show source content, not background.
    center = result.getpixel((90, 90))
    assert center != (255, 0, 0)


def test_render_icon_maskable_pads_content_inside_the_safe_zone():
    source = _rgba_square()
    spec = IconSpec(
        filename="icons/maskable-192.png", size=192, purpose="maskable", opaque_background=True, safe_zone_scale=0.8
    )
    result = _render_icon(source, spec, (0, 255, 0))
    assert result.size == (192, 192)
    # Corner is background padding; the icon content is confined to the center.
    assert result.getpixel((0, 0)) == (0, 255, 0)
    assert result.getpixel((96, 96)) != (0, 255, 0)


def test_render_splash_centers_icon_on_background_canvas():
    source = _rgba_square()
    spec = SplashSpec(filename="splash/apple-splash-750x1334.png", width=750, height=1334, media="(x)")
    result = _render_splash(source, spec, (0, 0, 255))
    assert result.size == (750, 1334)
    assert result.getpixel((0, 0)) == (0, 0, 255)
    assert result.getpixel((375, 667)) != (0, 0, 255)


def test_png_bytes_round_trips_through_pillow():
    data = png_bytes(_rgba_square(48))
    assert Image.open(BytesIO(data)).size == (48, 48)


def test_favicon_ico_bytes_contains_every_requested_size():
    data = favicon_ico_bytes(_rgba_square(64), (16, 32, 48))
    image = Image.open(BytesIO(data))
    sizes = {tuple(s) for s in image.info["sizes"]}
    assert sizes == {(16, 16), (32, 32), (48, 48)}


def test_manifest_dict_has_required_fields_and_icons():
    request = _request()
    icon_entries = [{"src": "icons/icon-48.png", "sizes": "48x48", "type": "image/png", "purpose": "any"}]
    manifest = manifest_dict(request, icon_entries)
    assert manifest["name"] == "Mon App"
    assert manifest["short_name"] == "MonApp"
    assert manifest["background_color"] == "#112233"
    assert manifest["theme_color"] == "#445566"
    assert manifest["icons"] == icon_entries
    assert json.dumps(manifest)  # serialisable


def test_snippet_html_includes_manifest_and_theme_color():
    html = snippet_html(_request(), True, True, ())
    assert '<link rel="manifest" href="manifest.webmanifest">' in html
    assert 'content="#445566"' in html
    assert 'apple-touch-icon' in html
    assert 'favicon.ico' in html


def test_snippet_html_omits_windows_meta_when_platform_disabled():
    html = snippet_html(_request(windows=False), True, True, ())
    assert "msapplication" not in html


def test_snippet_html_escapes_short_name_to_prevent_html_injection():
    request = _request()
    request.manifest.short_name = '"><script>'
    html = snippet_html(request, True, True, ())
    assert "<script>" not in html
    assert "&lt;" in html


def test_browserconfig_xml_embeds_tile_color():
    xml = browserconfig_xml("#abcdef")
    assert "<TileColor>#abcdef</TileColor>" in xml
    assert "square310x310logo" in xml
