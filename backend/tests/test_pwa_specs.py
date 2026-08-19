from app.engine.pwa.ios_splash import IOS_SPLASH_SCREENS
from app.engine.pwa.specs import (
    ANDROID_ICONS,
    ANDROID_ICON_SIZES,
    APPLE_ICONS,
    FAVICON_ICO_SIZES,
    FAVICON_PNG_SIZES,
    MASKABLE_ICONS,
    WINDOWS_TILE_SIZES,
)


def test_android_icons_cover_expected_sizes_with_unique_filenames():
    sizes = [spec.size for spec in ANDROID_ICONS]
    assert sizes == sorted(ANDROID_ICON_SIZES)
    assert len({spec.filename for spec in ANDROID_ICONS}) == len(ANDROID_ICONS)
    assert all(spec.purpose == "any" and spec.opaque_background is False for spec in ANDROID_ICONS)


def test_maskable_icons_are_opaque_with_safe_zone_padding():
    assert {spec.size for spec in MASKABLE_ICONS} == {192, 512}
    assert all(spec.purpose == "maskable" for spec in MASKABLE_ICONS)
    assert all(spec.opaque_background is True for spec in MASKABLE_ICONS)
    assert all(spec.safe_zone_scale == 0.8 for spec in MASKABLE_ICONS)


def test_apple_icons_include_the_default_filename():
    filenames = {spec.filename for spec in APPLE_ICONS}
    assert "apple-touch-icon.png" in filenames
    assert all(spec.opaque_background is True for spec in APPLE_ICONS)
    default = next(spec for spec in APPLE_ICONS if spec.filename == "apple-touch-icon.png")
    assert default.size == 180


def test_favicon_ico_sizes_are_a_superset_of_png_sizes():
    assert set(FAVICON_PNG_SIZES) <= set(FAVICON_ICO_SIZES)


def test_windows_tiles_are_square_only():
    assert WINDOWS_TILE_SIZES == (70, 150, 310)


def test_ios_splash_has_one_portrait_and_one_landscape_entry_per_device():
    assert len(IOS_SPLASH_SCREENS) % 2 == 0
    portrait = [s for s in IOS_SPLASH_SCREENS if "portrait" in s.media]
    landscape = [s for s in IOS_SPLASH_SCREENS if "orientation: landscape" in s.media]
    assert len(portrait) == len(landscape) == len(IOS_SPLASH_SCREENS) // 2
    # Every portrait entry has a matching landscape entry with swapped dimensions.
    landscape_dims = {(s.width, s.height) for s in landscape}
    for spec in portrait:
        assert (spec.height, spec.width) in landscape_dims


def test_ios_splash_landscape_shares_device_dimensions_with_portrait():
    """Landscape media queries must use portrait device-width/device-height
    since iOS/WebKit always reports those values regardless of actual orientation.
    Only the orientation keyword and image dimensions (width/height/filename) differ."""
    import re

    portrait = [s for s in IOS_SPLASH_SCREENS if "portrait" in s.media]
    landscape = [s for s in IOS_SPLASH_SCREENS if "orientation: landscape" in s.media]

    # For each portrait entry, find its matching landscape entry
    for portrait_spec in portrait:
        # Extract device-width, device-height, and ratio from media string
        portrait_match = re.search(
            r'\(device-width: ([\d.]+)px\).*\(device-height: ([\d.]+)px\).*\(-webkit-device-pixel-ratio: ([\d.]+)\)',
            portrait_spec.media,
        )
        assert portrait_match, f"Could not parse device dimensions from: {portrait_spec.media}"
        portrait_width, portrait_height, portrait_ratio = portrait_match.groups()

        # Find landscape entry for the same device (same device-width/height/ratio, opposite orientation)
        found_matching = False
        for landscape_spec in landscape:
            landscape_match = re.search(
                r'\(device-width: ([\d.]+)px\).*\(device-height: ([\d.]+)px\).*\(-webkit-device-pixel-ratio: ([\d.]+)\)',
                landscape_spec.media,
            )
            assert landscape_match, f"Could not parse device dimensions from: {landscape_spec.media}"
            landscape_width, landscape_height, landscape_ratio = landscape_match.groups()

            # Check if device dimensions and ratio match
            if (
                portrait_width == landscape_width
                and portrait_height == landscape_height
                and portrait_ratio == landscape_ratio
            ):
                # Verify image dimensions are swapped
                assert portrait_spec.width == landscape_spec.height, (
                    f"Portrait width {portrait_spec.width} should match landscape height {landscape_spec.height}"
                )
                assert portrait_spec.height == landscape_spec.width, (
                    f"Portrait height {portrait_spec.height} should match landscape width {landscape_spec.width}"
                )
                found_matching = True
                break

        assert found_matching, (
            f"No matching landscape entry found for portrait device "
            f"{portrait_width}x{portrait_height}@{portrait_ratio}"
        )
