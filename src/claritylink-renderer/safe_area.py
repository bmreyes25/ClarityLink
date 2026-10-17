"""Synthetic Display 1 safe-area gate; no Honda geometry or window admission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Rect":
        if not isinstance(value, Mapping):
            raise ValueError("rectangle must be an object")
        fields = tuple(value.get(key) for key in ("x", "y", "width", "height"))
        if any(isinstance(item, bool) or not isinstance(item, int) for item in fields):
            raise ValueError("rectangle coordinates must be integers")
        return cls(*fields)

    def valid_on(self, width: int, height: int) -> bool:
        return (self.x >= 0 and self.y >= 0 and self.width > 0 and self.height > 0
                and self.x + self.width <= width and self.y + self.height <= height)

    def contains_pixel(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


@dataclass(frozen=True)
class SafeAreaConfig:
    canvas_width: int
    canvas_height: int
    safe: Rect
    protected: tuple[Rect, ...]
    scale_numerator: int
    scale_denominator: int
    rotation_degrees: int
    provenance: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SafeAreaConfig":
        if not isinstance(value, Mapping):
            raise ValueError("safe-area config must be an object")
        raw_protected = value.get("protected")
        if not isinstance(raw_protected, list):
            raise ValueError("protected regions must be an array")
        return cls(
            value.get("canvas_width"), value.get("canvas_height"),
            Rect.from_mapping(value.get("safe")),
            tuple(Rect.from_mapping(item) for item in raw_protected),
            value.get("scale_numerator"), value.get("scale_denominator"),
            value.get("rotation_degrees"), value.get("provenance"),
        )

    def validate(self) -> None:
        numbers = (self.canvas_width, self.canvas_height, self.scale_numerator,
                   self.scale_denominator, self.rotation_degrees)
        if any(isinstance(item, bool) or not isinstance(item, int) for item in numbers):
            raise ValueError("geometry numbers must be integers")
        if (self.canvas_width, self.canvas_height) != (800, 480):
            raise ValueError("only the modeled 800x480 logical canvas is supported")
        if not self.safe.valid_on(self.canvas_width, self.canvas_height):
            raise ValueError("safe rectangle is invalid")
        if any(not rect.valid_on(self.canvas_width, self.canvas_height) for rect in self.protected):
            raise ValueError("protected rectangle is invalid")
        if self.scale_numerator <= 0 or self.scale_denominator <= 0:
            raise ValueError("scale must be positive")
        # Pixel masking cannot enforce an unknown physical transform. A distinct
        # physical projection would need another reviewed backend contract.
        if self.scale_numerator != self.scale_denominator or self.rotation_degrees != 0:
            raise ValueError("nonidentity physical transform is not admitted")
        if self.provenance != "SYNTHETIC_TEST_ONLY":
            raise ValueError("Honda safe-area provenance is not established")

    def permits_pixel(self, x: int, y: int) -> bool:
        return self.safe.contains_pixel(x, y) and not any(
            rect.contains_pixel(x, y) for rect in self.protected)


class SafeAreaGate:
    """Host simulator gate; alpha-zero pixels outside admitted synthetic region."""

    def __init__(self, config: SafeAreaConfig):
        self.config = config
        self.surface_available = True
        self.warning_active = False
        self.geometry_valid = False

    def start(self) -> None:
        self.config.validate()
        self.geometry_valid = True

    @property
    def active(self) -> bool:
        return self.geometry_valid and self.surface_available and not self.warning_active

    def surface_lost(self) -> None:
        self.surface_available = False

    def surface_restored(self) -> None:
        self.surface_available = True

    def warning_preempted(self) -> None:
        self.warning_active = True

    def warning_cleared(self) -> None:
        self.warning_active = False

    def update_geometry(self, config: SafeAreaConfig) -> None:
        self.geometry_valid = False
        self.config = config
        config.validate()
        self.geometry_valid = True

    def clip(self, frame: Any) -> Any:
        if not self.active:
            raise ValueError("safe-area output is withdrawn")
        frame.validate(require_cpu=True)
        width, height = self.config.canvas_width, self.config.canvas_height
        if (frame.width, frame.height, frame.row_stride, frame.rotation_degrees) != (
                width, height, width * 4, 0):
            raise ValueError("frame geometry does not match safe-area canvas")
        if frame.crop is not None and frame.crop != (0, 0, width, height):
            raise ValueError("cropped source transform is not admitted")
        from dataclasses import replace
        source = frame.rgba
        assert source is not None
        output = bytearray(len(source))
        safe = self.config.safe
        for y in range(safe.y, safe.y + safe.height):
            for x in range(safe.x, safe.x + safe.width):
                if self.config.permits_pixel(x, y):
                    offset = (y * width + x) * 4
                    output[offset:offset + 4] = source[offset:offset + 4]
        return replace(frame, rgba=bytes(output))
