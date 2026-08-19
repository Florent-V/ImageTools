"""Apple `apple-touch-startup-image` splash screen table.

Apple does not publish an official splash-screen size list; these are the
widely-used device pixel dimensions, one portrait + one landscape entry per
device class. This is the one table in the PWA kit expected to need
periodic updates as Apple ships new screen sizes — kept isolated here so
that maintenance never touches the stable icon specs in `specs.py`.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SplashSpec:
    filename: str
    width: int
    height: int
    media: str


# name, portrait width (px), portrait height (px), device-pixel-ratio
_DEVICES: tuple[tuple[str, int, int, float], ...] = (
    ("iphone-se", 640, 1136, 2),
    ("iphone-8", 750, 1334, 2),
    ("iphone-8-plus", 1242, 2208, 3),
    ("iphone-x", 1125, 2436, 3),
    ("iphone-xr", 828, 1792, 2),
    ("iphone-xs-max", 1242, 2688, 3),
    ("iphone-12", 1170, 2532, 3),
    ("iphone-12-pro-max", 1284, 2778, 3),
    ("iphone-14-pro", 1179, 2556, 3),
    ("iphone-14-pro-max", 1290, 2796, 3),
    ("ipad-10-2", 1620, 2160, 2),
    ("ipad-pro-11", 1668, 2388, 2),
    ("ipad-pro-12-9", 2048, 2732, 2),
)


def _media(width_pt: float, height_pt: float, ratio: float, orientation: str) -> str:
    return (
        f"(device-width: {width_pt:g}px) and (device-height: {height_pt:g}px) "
        f"and (-webkit-device-pixel-ratio: {ratio:g}) and (orientation: {orientation})"
    )


def _build_splash_specs() -> tuple[SplashSpec, ...]:
    specs: list[SplashSpec] = []
    for _name, width_px, height_px, ratio in _DEVICES:
        width_pt, height_pt = width_px / ratio, height_px / ratio
        specs.append(
            SplashSpec(
                filename=f"splash/apple-splash-{width_px}x{height_px}.png",
                width=width_px,
                height=height_px,
                media=_media(width_pt, height_pt, ratio, "portrait"),
            )
        )
        specs.append(
            SplashSpec(
                filename=f"splash/apple-splash-{height_px}x{width_px}.png",
                width=height_px,
                height=width_px,
                media=_media(width_pt, height_pt, ratio, "landscape"),
            )
        )
    return tuple(specs)


IOS_SPLASH_SCREENS: tuple[SplashSpec, ...] = _build_splash_specs()
