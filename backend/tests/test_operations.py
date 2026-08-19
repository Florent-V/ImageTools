import pytest
from PIL import Image

from app.engine.operations import crop, registry, resize, rotate
from app.errors import ImageError
from app.schemas.operations import CropOp, ResizeOp, RotateOp


def _image(size=(400, 300)) -> Image.Image:
    return Image.new("RGB", size, (10, 20, 30))


def test_width_only_derives_height_from_the_ratio():
    result = resize.apply(_image((400, 300)), ResizeOp(op="resize", width=200))
    assert result.size == (200, 150)


def test_both_dimensions_with_ratio_kept_fits_inside_the_box():
    # 400x300 into a 200x200 box: the width is the binding constraint.
    result = resize.apply(
        _image((400, 300)), ResizeOp(op="resize", width=200, height=200, keep_ratio=True)
    )
    assert result.size == (200, 150)


def test_ratio_unlocked_stretches_to_exactly_what_was_asked():
    result = resize.apply(
        _image((400, 300)), ResizeOp(op="resize", width=200, height=200, keep_ratio=False)
    )
    assert result.size == (200, 200)


def test_no_upscale_leaves_a_smaller_image_untouched():
    result = resize.apply(
        _image((100, 80)), ResizeOp(op="resize", width=500, no_upscale=True)
    )
    assert result.size == (100, 80)


def test_no_upscale_disabled_does_enlarge():
    result = resize.apply(
        _image((100, 80)), ResizeOp(op="resize", width=200, no_upscale=False)
    )
    assert result.size == (200, 160)


def test_percent_scales_both_sides():
    result = resize.apply(_image((400, 300)), ResizeOp(op="resize", percent=50))
    assert result.size == (200, 150)


def test_crop_returns_the_requested_rectangle():
    result = crop.apply(_image((400, 300)), CropOp(op="crop", x=10, y=20, width=100, height=50))
    assert result.size == (100, 50)


def test_crop_past_the_right_edge_is_refused():
    # Silently clamping would hand back an image with dimensions the user
    # never asked for. Refusing is the honest answer.
    with pytest.raises(ImageError) as excinfo:
        crop.apply(_image((400, 300)), CropOp(op="crop", x=350, y=0, width=100, height=50))
    assert excinfo.value.code == "INVALID_OPERATION"


def test_rotating_90_degrees_turns_clockwise():
    # Dimensions swap under a quarter turn in either direction, so the size
    # assertion alone cannot tell clockwise from counter-clockwise — and the
    # mapping to Pillow's constants is inverted on purpose. Pin a corner:
    # turning clockwise brings the bottom-left pixel to the top-left.
    source = Image.new("RGB", (2, 2))
    source.putpixel((0, 0), (255, 0, 0))  # top-left, red
    source.putpixel((1, 0), (0, 255, 0))  # top-right, green
    source.putpixel((0, 1), (0, 0, 255))  # bottom-left, blue
    source.putpixel((1, 1), (255, 255, 0))  # bottom-right, yellow

    result = rotate.apply(source, RotateOp(op="rotate", degrees=90))

    assert result.getpixel((0, 0)) == (0, 0, 255)
    assert result.getpixel((1, 0)) == (255, 0, 0)
    assert rotate.apply(_image((400, 300)), RotateOp(op="rotate", degrees=90)).size == (
        300,
        400,
    )


def test_horizontal_flip_keeps_dimensions_and_moves_pixels():
    source = Image.new("RGB", (2, 1))
    source.putpixel((0, 0), (255, 0, 0))
    source.putpixel((1, 0), (0, 0, 255))

    result = rotate.apply(source, RotateOp(op="rotate", flip_horizontal=True))

    assert result.size == (2, 1)
    assert result.getpixel((0, 0)) == (0, 0, 255)


def test_operations_run_in_the_order_they_were_given():
    # Resize then crop, versus crop then resize, are different pictures.
    # The array order decides; the engine never reorders.
    ops = [
        ResizeOp(op="resize", width=200, height=150, keep_ratio=False),
        CropOp(op="crop", x=0, y=0, width=100, height=100),
    ]
    result = registry.apply_operations(_image((400, 300)), ops)
    assert result.size == (100, 100)


def test_the_reverse_order_yields_a_different_picture():
    # Cropping 100x100 out of a 400x300 image first, then resizing, gives
    # 50x50 rather than the 100x100 above — proof the order is not normalised.
    ops = [
        CropOp(op="crop", x=0, y=0, width=100, height=100),
        ResizeOp(op="resize", width=50),
    ]
    result = registry.apply_operations(_image((400, 300)), ops)
    assert result.size == (50, 50)
