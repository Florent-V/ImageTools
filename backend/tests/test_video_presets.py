from app.engine.video.presets import CONTAINERS, CRF_BY_QUALITY, FPS_OPTIONS, RATIO_PRESETS, RESOLUTION_LADDER


def test_ratio_presets_cover_expected_platforms():
    ids = {p.id for p in RATIO_PRESETS}
    assert ids == {
        "tiktok", "instagram_square", "instagram_portrait", "youtube",
        "cinema_21_9", "classic_4_3", "libre",
    }


def test_libre_preset_has_no_ratio():
    libre = next(p for p in RATIO_PRESETS if p.id == "libre")
    assert libre.ratio is None


def test_ratio_presets_have_no_resolutions_field():
    for preset in RATIO_PRESETS:
        assert not hasattr(preset, "resolutions")


def test_new_presets_have_expected_ratios():
    by_id = {p.id: p for p in RATIO_PRESETS}
    assert by_id["cinema_21_9"].ratio == (21, 9)
    assert by_id["classic_4_3"].ratio == (4, 3)


def test_crf_by_quality_covers_all_four_tiers_in_increasing_order():
    assert set(CRF_BY_QUALITY.keys()) == {"light", "recommended", "strong", "max"}
    assert CRF_BY_QUALITY["max"] < CRF_BY_QUALITY["light"] < CRF_BY_QUALITY["recommended"] < CRF_BY_QUALITY["strong"]


def test_resolution_ladder_has_six_heights_descending():
    heights = [h for _, h in RESOLUTION_LADDER]
    assert heights == [2160, 1440, 1080, 720, 480, 360]


def test_containers_cover_expected_set():
    ids = {c[0] for c in CONTAINERS}
    assert ids == {"mp4", "mov", "mkv", "webm"}


def test_fps_options_are_original_30_60():
    assert FPS_OPTIONS == ["original", 30, 60]
