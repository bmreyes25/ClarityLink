from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-renderer"))

from display_geometry import (  # noqa: E402
    Landmark,
    PhotoCalibration,
    Rect,
    ScalePolicy,
    annotated_svg,
    map_image,
)


def test_exact_stretch_maps_source_to_offset_view() -> None:
    result = map_image(320, 180, Rect(11, 7, 651, 367), policy=ScalePolicy.STRETCH)
    assert result.image_bounds == Rect(11, 7, 651, 367)
    assert result.visible_display_bounds == Rect(11, 7, 651, 367)
    assert result.source_crop == Rect(0, 0, 320, 180)


def test_fit_center_preserves_aspect_ratio_with_letterbox() -> None:
    result = map_image(320, 180, Rect(10, 20, 610, 420), policy=ScalePolicy.FIT_CENTER)
    assert result.image_bounds == Rect(10, 51.25, 610, 388.75)
    assert result.visible_display_bounds == result.image_bounds
    assert result.source_crop == Rect(0, 0, 320, 180)


def test_center_crop_reports_source_crop_and_visible_region() -> None:
    result = map_image(320, 180, Rect(0, 0, 400, 400), policy=ScalePolicy.CENTER_CROP)
    assert result.image_bounds == Rect(-155.55555555555554, 0, 555.5555555555555, 400)
    assert result.visible_display_bounds == Rect(0, 0, 400, 400)
    assert result.source_crop.left == pytest.approx(70)
    assert result.source_crop.right == pytest.approx(250)
    assert result.source_crop.top == pytest.approx(0)
    assert result.source_crop.bottom == pytest.approx(180)


def test_known_clip_and_landmark_visibility_are_explicit() -> None:
    result = map_image(
        100, 50, Rect(20, 30, 220, 130), clip_bounds=Rect(70, 30, 170, 130),
        landmarks=(Landmark("inside", 25, 25), Landmark("outside", 5, 25)),
    )
    assert result.visible_display_bounds == Rect(70, 30, 170, 130)
    assert result.source_crop == Rect(25, 0, 75, 50)
    assert result.landmarks[0].visible_after_clip
    assert not result.landmarks[1].visible_after_clip


def test_disjoint_clip_has_no_visible_display_or_source_region() -> None:
    result = map_image(100, 50, Rect(20, 30, 220, 130),
                       clip_bounds=Rect(300, 300, 400, 400))
    assert result.visible_display_bounds is None
    assert result.source_crop is None


def test_clip_limited_to_fit_center_letterbox_has_no_visible_source_region() -> None:
    result = map_image(100, 50, Rect(0, 0, 100, 100),
                       policy=ScalePolicy.FIT_CENTER,
                       clip_bounds=Rect(0, 0, 100, 20))
    assert result.image_bounds == Rect(0, 25, 100, 75)
    assert result.visible_display_bounds is None
    assert result.source_crop is None


def test_optional_projective_photo_calibration_maps_landmark_only() -> None:
    calibration = PhotoCalibration((2, 0, 5, 0, 2, 9, 0, 0, 1))
    result = map_image(
        100, 50, Rect(10, 20, 210, 120),
        landmarks=(Landmark("center", 50, 25),), photo_calibration=calibration,
    )
    assert result.landmarks[0].display == (110, 70)
    assert result.landmarks[0].photo == (225, 149)
    assert result.physical_visible_bounds is None


@pytest.mark.parametrize("dimensions", [(0, 1), (1, 0), (-2, 3), (True, 4)])
def test_invalid_source_dimensions_fail_closed(dimensions) -> None:
    with pytest.raises(ValueError):
        map_image(*dimensions, Rect(0, 0, 10, 10))


def test_invalid_view_clip_and_calibration_fail_closed() -> None:
    with pytest.raises(ValueError):
        Rect(1, 1, 1, 2)
    with pytest.raises(ValueError):
        map_image(10, 10, Rect(0, 0, 10, 10), policy="unknown")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="invertible"):
        PhotoCalibration((1, 0, 0, 0, 0, 0, 0, 0, 1))


def test_annotated_synthetic_svg_marks_bounds_and_unknown_physical_area() -> None:
    result = map_image(
        320, 180, Rect(24, 16, 664, 416), policy=ScalePolicy.CENTER_CROP,
        clip_bounds=Rect(40, 32, 640, 400), landmarks=(Landmark("center", 160, 90),),
    )
    image = annotated_svg(result, width=800, height=500)
    assert image.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert "destination View" in image
    assert "rendered image" in image
    assert "effective clip" in image
    assert "visible display region" in image
    assert "center" in image
    assert "Physical bounds: UNKNOWN" in image


@pytest.mark.parametrize("canvas", [(0, 10), (10, 0), (float("nan"), 10),
                                     (10, float("inf")), (True, 10)])
def test_invalid_svg_canvas_dimensions_fail_closed(canvas) -> None:
    result = map_image(10, 10, Rect(0, 0, 10, 10))
    with pytest.raises(ValueError, match="positive integers"):
        annotated_svg(result, width=canvas[0], height=canvas[1])  # type: ignore[arg-type]
