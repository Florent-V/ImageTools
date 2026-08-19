from app.engine import target_size
from app.engine.decoder import decode
from tests import factories


def test_result_lands_under_the_requested_size():
    decoded = decode(factories.make_photo((600, 400)))

    data, quality = target_size.encode_to_target(decoded.image, "jpeg", 20, None, None)

    assert len(data) <= 20 * 1024
    assert 1 <= quality <= 100


def test_the_search_is_bounded(monkeypatch):
    # A runaway loop on a large photo would hang a request. Count the encodes.
    decoded = decode(factories.make_photo((600, 400)))
    calls = []

    real_encode = target_size.encode

    def counting_encode(*args, **kwargs):
        calls.append(1)
        return real_encode(*args, **kwargs)

    monkeypatch.setattr(target_size, "encode", counting_encode)
    target_size.encode_to_target(decoded.image, "jpeg", 20, None, None)

    assert len(calls) <= target_size.MAX_ATTEMPTS


def test_an_impossible_target_returns_the_smallest_it_can_make():
    # 1 KB is unreachable for this photo. Returning the best effort beats
    # failing — the caller can see the real size in the response headers.
    decoded = decode(factories.make_photo((600, 400)))

    data, quality = target_size.encode_to_target(decoded.image, "jpeg", 1, None, None)

    assert quality == 1
    assert len(data) > 0
