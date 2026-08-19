import json
from zipfile import ZipFile
from io import BytesIO

from PIL import Image

from app.engine.pwa.generator import generate_kit
from app.schemas.pwa import PwaGenerateRequest


def _source(size: tuple[int, int] = (300, 300)) -> Image.Image:
    return Image.new("RGBA", size, (10, 20, 30, 255))


def _request(**platform_overrides) -> PwaGenerateRequest:
    payload = {
        "crop": {"x": 0, "y": 0, "width": 300, "height": 300},
        "background_color": "#FFFFFF",
        "manifest": {"name": "Mon App", "short_name": "MonApp", "theme_color": "#000000"},
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


def test_generate_kit_with_everything_enabled_includes_every_platform_file():
    kit = generate_kit(_source(), _request())
    with ZipFile(BytesIO(kit.zip_bytes)) as archive:
        names = set(archive.namelist())

    assert "manifest.webmanifest" in names
    assert "snippet.html" in names
    assert "icons/icon-192.png" in names
    assert "icons/maskable-512.png" in names
    assert "icons/apple-touch-icon-180.png" in names
    assert "apple-touch-icon.png" in names
    assert "favicon.ico" in names
    assert "favicon-32x32.png" in names
    assert "windows/tile-150.png" in names
    assert "windows/browserconfig.xml" in names
    assert any(name.startswith("splash/apple-splash-") for name in names)
    assert kit.file_count == len(names)


def test_generate_kit_omits_disabled_platform_files():
    kit = generate_kit(_source(), _request(windows=False, splash=False, ios=False))
    with ZipFile(BytesIO(kit.zip_bytes)) as archive:
        names = set(archive.namelist())

    assert not any(name.startswith("windows/") for name in names)
    assert not any(name.startswith("splash/") for name in names)
    assert "apple-touch-icon.png" not in names
    # Always-on outputs stay present regardless of platform toggles.
    assert "manifest.webmanifest" in names
    assert "icons/icon-192.png" in names


def test_generate_kit_manifest_lists_only_android_and_maskable_icons():
    kit = generate_kit(_source(), _request())
    with ZipFile(BytesIO(kit.zip_bytes)) as archive:
        manifest = json.loads(archive.read("manifest.webmanifest"))

    manifest_srcs = {icon["src"] for icon in manifest["icons"]}
    assert "icons/icon-192.png" in manifest_srcs
    assert "icons/maskable-512.png" in manifest_srcs
    assert not any(src.startswith("icons/apple-touch-icon") for src in manifest_srcs)


def test_generate_kit_crops_non_square_source_to_the_requested_square_region():
    # A wide source; the crop rect picks a square region from it.
    source = Image.new("RGBA", (400, 200), (0, 0, 0, 255))
    request = _request(favicon=False, windows=False, splash=False, ios=False)
    request.crop.x, request.crop.y, request.crop.width, request.crop.height = 0, 0, 200, 200
    kit = generate_kit(source, request)
    with ZipFile(BytesIO(kit.zip_bytes)) as archive:
        icon = Image.open(BytesIO(archive.read("icons/icon-192.png")))
    assert icon.size == (192, 192)
