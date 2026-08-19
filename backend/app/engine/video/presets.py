from dataclasses import dataclass

from app.schemas.video import VideoQuality


@dataclass(frozen=True)
class RatioPreset:
    id: str
    label: str
    description: str
    ratio: tuple[int, int] | None  # None = "Libre", no fixed ratio


RATIO_PRESETS: list[RatioPreset] = [
    RatioPreset("tiktok", "TikTok / Reels / Shorts / Stories", "Format vertical plein écran.", (9, 16)),
    RatioPreset("instagram_square", "Instagram carré", "Publication carrée.", (1, 1)),
    RatioPreset("instagram_portrait", "Instagram portrait", "Publication portrait.", (4, 5)),
    RatioPreset("youtube", "YouTube / Paysage", "Format paysage classique.", (16, 9)),
    RatioPreset("cinema_21_9", "Cinéma", "Format ultra-large cinématographique.", (21, 9)),
    RatioPreset("classic_4_3", "Classique", "Format 4:3 traditionnel.", (4, 3)),
    RatioPreset("libre", "Libre", "Recadrage manuel, sans ratio imposé.", None),
]

CRF_BY_QUALITY: dict[VideoQuality, int] = {
    "light": 20,
    "recommended": 23,
    "strong": 28,
    "max": 17,
}

# (label, height) — width is derived client-side from the crop rect's aspect ratio.
RESOLUTION_LADDER: list[tuple[str, int]] = [
    ("4K", 2160),
    ("2K", 1440),
    ("1080p", 1080),
    ("720p", 720),
    ("480p", 480),
    ("360p", 360),
]

CONTAINERS: list[tuple[str, str]] = [
    ("mp4", "MP4"),
    ("mov", "MOV"),
    ("mkv", "MKV"),
    ("webm", "WebM"),
]

FPS_OPTIONS: list[str | int] = ["original", 30, 60]
