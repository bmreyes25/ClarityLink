"""Pure geometry model for testing a decoded image in a destination view.

This module describes coordinate transforms only. It does not create a display,
admit a frame, infer a vehicle safe area, or supply default display dimensions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html import escape
import math
from typing import Iterable


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("rectangle coordinates must be finite")
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("rectangle must have positive width and height")

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def intersect(self, other: "Rect") -> "Rect | None":
        left, top = max(self.left, other.left), max(self.top, other.top)
        right, bottom = min(self.right, other.right), min(self.bottom, other.bottom)
        if right <= left or bottom <= top:
            return None
        return Rect(left, top, right, bottom)


class ScalePolicy(str, Enum):
    STRETCH = "stretch"
    FIT_CENTER = "fit_center"
    CENTER_CROP = "center_crop"


@dataclass(frozen=True)
class PhotoCalibration:
    """Projective transform from display coordinates to photo pixel coordinates.

    The row-major 3x3 matrix maps (x, y, 1) to homogeneous photo coordinates.
    Calibration is optional and must come from measured landmarks; no transform
    is inferred from an uncalibrated photograph.
    """

    matrix: tuple[float, float, float, float, float, float, float, float, float]

    def __post_init__(self) -> None:
        if len(self.matrix) != 9 or not all(math.isfinite(value) for value in self.matrix):
            raise ValueError("photo calibration requires nine finite coefficients")
        a, b, c, d, e, f, g, h, i = self.matrix
        determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
        if abs(determinant) < 1e-12:
            raise ValueError("photo calibration must be invertible")

    def map_point(self, x: float, y: float) -> tuple[float, float]:
        a, b, c, d, e, f, g, h, i = self.matrix
        denominator = g * x + h * y + i
        if not math.isfinite(denominator) or abs(denominator) < 1e-12:
            raise ValueError("point maps to infinity under photo calibration")
        px = (a * x + b * y + c) / denominator
        py = (d * x + e * y + f) / denominator
        if not math.isfinite(px) or not math.isfinite(py):
            raise ValueError("calibrated point is not finite")
        return px, py


@dataclass(frozen=True)
class Landmark:
    name: str
    x: float
    y: float


@dataclass(frozen=True)
class MappedLandmark:
    name: str
    source: tuple[float, float]
    display: tuple[float, float]
    visible_in_view: bool
    visible_after_clip: bool
    photo: tuple[float, float] | None


@dataclass(frozen=True)
class GeometryResult:
    source_bounds: Rect
    view_bounds: Rect
    image_bounds: Rect
    view_clip: Rect | None
    visible_display_bounds: Rect | None
    source_crop: Rect | None
    physical_visible_bounds: None
    landmarks: tuple[MappedLandmark, ...]


def map_image(
    source_width: int,
    source_height: int,
    view_bounds: Rect,
    *,
    policy: ScalePolicy = ScalePolicy.STRETCH,
    clip_bounds: Rect | None = None,
    landmarks: Iterable[Landmark] = (),
    photo_calibration: PhotoCalibration | None = None,
) -> GeometryResult:
    """Map a source image into a view and report crop/clipping explicitly."""
    if (not isinstance(source_width, int) or isinstance(source_width, bool)
            or not isinstance(source_height, int) or isinstance(source_height, bool)
            or source_width <= 0 or source_height <= 0):
        raise ValueError("source dimensions must be positive integers")
    if not isinstance(policy, ScalePolicy):
        raise ValueError("unknown scale policy")

    source = Rect(0, 0, source_width, source_height)
    sx, sy = view_bounds.width / source_width, view_bounds.height / source_height
    if policy is ScalePolicy.STRETCH:
        image = view_bounds
    else:
        scale = (min if policy is ScalePolicy.FIT_CENTER else max)(sx, sy)
        width, height = source_width * scale, source_height * scale
        left = view_bounds.left + (view_bounds.width - width) / 2
        top = view_bounds.top + (view_bounds.height - height) / 2
        image = Rect(left, top, left + width, top + height)
        sx = sy = scale

    effective_clip = view_bounds if clip_bounds is None else view_bounds.intersect(clip_bounds)
    visible = None if effective_clip is None else image.intersect(effective_clip)
    if visible is None:
        crop = None
    else:
        crop_left = max(0.0, (visible.left - image.left) / sx)
        crop_top = max(0.0, (visible.top - image.top) / sy)
        crop_right = min(float(source_width), (visible.right - image.left) / sx)
        crop_bottom = min(float(source_height), (visible.bottom - image.top) / sy)
        crop = Rect(crop_left, crop_top, crop_right, crop_bottom)

    mapped = []
    for landmark in landmarks:
        if not (math.isfinite(landmark.x) and math.isfinite(landmark.y)):
            raise ValueError("landmark coordinates must be finite")
        px, py = image.left + landmark.x * sx, image.top + landmark.y * sy
        inside_view = (0 <= landmark.x < source_width and 0 <= landmark.y < source_height
                       and view_bounds.left <= px < view_bounds.right
                       and view_bounds.top <= py < view_bounds.bottom)
        inside_clip = (inside_view and effective_clip is not None
                       and effective_clip.left <= px < effective_clip.right
                       and effective_clip.top <= py < effective_clip.bottom)
        photo = photo_calibration.map_point(px, py) if photo_calibration else None
        mapped.append(MappedLandmark(landmark.name, (landmark.x, landmark.y), (px, py),
                                     inside_view, inside_clip, photo))

    return GeometryResult(source, view_bounds, image, effective_clip, visible, crop, None,
                          tuple(mapped))


def annotated_svg(result: GeometryResult, *, width: int, height: int) -> str:
    """Render an annotated synthetic coordinate diagram as standalone SVG."""
    if (not isinstance(width, int) or isinstance(width, bool)
            or not isinstance(height, int) or isinstance(height, bool)
            or width <= 0 or height <= 0):
        raise ValueError("canvas dimensions must be positive integers")
    min_x = min(0.0, result.view_bounds.left, result.image_bounds.left)
    min_y = min(0.0, result.view_bounds.top, result.image_bounds.top)
    max_x = max(result.view_bounds.right, result.image_bounds.right)
    max_y = max(result.view_bounds.bottom, result.image_bounds.bottom)
    sx, sy = width / (max_x - min_x), height / (max_y - min_y)
    scale = min(sx, sy)
    ox, oy = -min_x * scale, -min_y * scale

    def xy(x: float, y: float) -> tuple[float, float]:
        return ox + x * scale, oy + y * scale

    def rect_svg(rect: Rect, color: str, label: str, dashed: bool = False) -> str:
        x, y = xy(rect.left, rect.top)
        dash = ' stroke-dasharray="8 5"' if dashed else ""
        return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{rect.width*scale:.2f}" '
                f'height="{rect.height*scale:.2f}" fill="none" stroke="{color}" '
                f'stroke-width="3"{dash}/><text x="{x+5:.2f}" y="{y+18:.2f}" '
                f'font-family="sans-serif" font-size="14" fill="{color}">'
                f'{escape(label)}</text>')

    elements = [
        rect_svg(result.view_bounds, "#1976d2", "destination View"),
        rect_svg(result.image_bounds, "#2e7d32", "rendered image"),
    ]
    if result.view_clip is not None:
        elements.append(rect_svg(result.view_clip, "#c62828", "effective clip", True))
    if result.visible_display_bounds is not None:
        elements.append(rect_svg(result.visible_display_bounds, "#6a1b9a", "visible display region"))
    for landmark in result.landmarks:
        x, y = xy(*landmark.display)
        elements.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#ff8f00"/>'
                        f'<text x="{x+7:.2f}" y="{y-7:.2f}" font-family="sans-serif" '
                        f'font-size="13" fill="#222">{escape(landmark.name)}</text>')
    note = "Physical bounds: UNKNOWN" if result.physical_visible_bounds is None else ""
    elements.append(f'<text x="12" y="{height-10}" font-family="sans-serif" '
                    f'font-size="14" fill="#333">{note}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#fff"/>'
            + "".join(elements) + "</svg>\n")
