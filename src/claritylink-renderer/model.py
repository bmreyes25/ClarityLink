"""Host-testable Display 1 frame contract and synthetic renderer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol


DISPLAY_ID = 1
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
PIXEL_FORMAT = "RGBA_8888"
MAX_FRAME_BYTES = DISPLAY_WIDTH * DISPLAY_HEIGHT * 4


@dataclass(frozen=True)
class DisplayTarget:
    display_id: int = DISPLAY_ID
    width: int = DISPLAY_WIDTH
    height: int = DISPLAY_HEIGHT

    def validate(self) -> None:
        if self.display_id != DISPLAY_ID:
            raise ValueError("ClarityLink output target must be Android Display 1")
        if (self.width, self.height) != (DISPLAY_WIDTH, DISPLAY_HEIGHT):
            raise ValueError("Display 1 contract is 800x480")


@dataclass(frozen=True)
class DecodedFrame:
    """Future decoder boundary. row_stride is bytes, independent of fbdev stride."""

    width: int
    height: int
    pixel_format: str
    row_stride: int
    presentation_time_ns: int
    rgba: Optional[bytes] = None
    surface_token: Optional[str] = None
    rotation_degrees: int = 0
    crop: Optional[tuple[int, int, int, int]] = None

    def validate(self, require_cpu: bool = False) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("frame dimensions must be positive")
        if self.width > 3840 or self.height > 2160:
            raise ValueError("frame dimensions exceed the supported input limit")
        if self.pixel_format != PIXEL_FORMAT:
            raise ValueError("only RGBA_8888 frames are supported by this prototype")
        if self.row_stride < self.width * 4:
            raise ValueError("row_stride is smaller than one RGBA row")
        if self.rotation_degrees not in (0, 90, 180, 270):
            raise ValueError("rotation_degrees must be 0, 90, 180, or 270")
        if self.crop is not None:
            left, top, right, bottom = self.crop
            if not (0 <= left < right <= self.width and 0 <= top < bottom <= self.height):
                raise ValueError("crop must be a non-empty rectangle inside the frame")
        if self.rgba is None:
            if require_cpu or not self.surface_token:
                raise ValueError("CPU RGBA bytes are required by the current backend")
        elif len(self.rgba) < self.row_stride * self.height:
            raise ValueError("RGBA buffer is shorter than row_stride × height")


class FrameSource(Protocol):
    def next_frame(self) -> DecodedFrame:
        """Return one owned frame; caller releases it after backend submission."""


class Display1OutputBackend(Protocol):
    def attach(self, target: DisplayTarget) -> None: ...

    def submit(self, frame: DecodedFrame) -> None: ...

    def clear(self) -> None: ...

    def close(self) -> None: ...


class ClarityLinkRenderer:
    def __init__(self, backend: Display1OutputBackend, target: DisplayTarget = DisplayTarget()):
        self.backend = backend
        self.target = target
        self.started = False

    def start(self) -> None:
        if self.started:
            raise RuntimeError("renderer is already started")
        self.target.validate()
        self.backend.attach(self.target)
        self.started = True

    def submit(self, frame: DecodedFrame) -> None:
        if not self.started:
            raise RuntimeError("renderer is not started")
        frame.validate()
        self.backend.submit(frame)

    def close(self) -> None:
        if not self.started:
            return
        try:
            self.backend.clear()
        finally:
            try:
                self.backend.close()
            finally:
                self.started = False


class MockDisplay1Backend:
    """Deterministic host backend. It does not emulate Android output."""

    def __init__(self) -> None:
        self.target: Optional[DisplayTarget] = None
        self.frames: list[DecodedFrame] = []
        self.events: list[str] = []

    def attach(self, target: DisplayTarget) -> None:
        if self.target is not None:
            raise RuntimeError("backend is already attached")
        target.validate()
        self.target = target
        self.events.append("attach")

    def submit(self, frame: DecodedFrame) -> None:
        if self.target is None:
            raise RuntimeError("backend is detached")
        frame.validate(require_cpu=True)
        self.frames.append(frame)
        self.events.append("submit")

    def clear(self) -> None:
        self.frames.clear()
        self.events.append("clear")

    def close(self) -> None:
        self.target = None
        self.events.append("close")


_FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "11100"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    " ": ("00000",) * 7,
}


def _fill(buf: bytearray, x: int, y: int, width: int, height: int, rgba: bytes) -> None:
    for row in range(max(0, y), min(DISPLAY_HEIGHT, y + height)):
        left = max(0, x)
        right = min(DISPLAY_WIDTH, x + width)
        if left < right:
            start = (row * DISPLAY_WIDTH + left) * 4
            buf[start : start + (right - left) * 4] = rgba * (right - left)


def _text(buf: bytearray, text: str, x: int, y: int, scale: int, color: bytes) -> None:
    cursor = x
    for char in text:
        glyph = _FONT.get(char, _FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    _fill(buf, cursor + gx * scale, y + gy * scale, scale, scale, color)
        cursor += 6 * scale


class SyntheticPatternSource:
    """Produces an 800×480 RGBA pattern with border, grid, label and animation."""

    def __init__(self) -> None:
        self.counter = 0

    def next_frame(self, now: Optional[datetime] = None) -> DecodedFrame:
        now = now or datetime.now(timezone.utc)
        self.counter += 1
        buf = bytearray(MAX_FRAME_BYTES)
        bg = bytes((0, 0, 0, 255))
        grid = bytes((28, 62, 78, 255))
        border = bytes((0, 210, 255, 255))
        white = bytes((245, 250, 255, 255))
        moving = bytes((255, 80, 36, 255))
        _fill(buf, 0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, bg)
        for x in range(0, DISPLAY_WIDTH, 80):
            _fill(buf, x, 0, 1, DISPLAY_HEIGHT, grid)
        for y in range(0, DISPLAY_HEIGHT, 60):
            _fill(buf, 0, y, DISPLAY_WIDTH, 1, grid)
        _fill(buf, 0, 0, DISPLAY_WIDTH, 3, border)
        _fill(buf, 0, DISPLAY_HEIGHT - 3, DISPLAY_WIDTH, 3, border)
        _fill(buf, 0, 0, 3, DISPLAY_HEIGHT, border)
        _fill(buf, DISPLAY_WIDTH - 3, 0, 3, DISPLAY_HEIGHT, border)
        _text(buf, "CLARITYLINK DISPLAY 1", 24, 24, 3, white)
        stamp = now.astimezone(timezone.utc).strftime("%H:%M:%S")
        _text(buf, f"FRAME {self.counter:06d} - {stamp}", 24, 54, 2, white)
        x = 20 + (self.counter * 17) % (DISPLAY_WIDTH - 120)
        _fill(buf, x, 210, 96, 48, moving)
        _fill(buf, x + 4, 214, 88, 40, bg)
        return DecodedFrame(
            width=DISPLAY_WIDTH,
            height=DISPLAY_HEIGHT,
            pixel_format=PIXEL_FORMAT,
            row_stride=DISPLAY_WIDTH * 4,
            presentation_time_ns=int(now.timestamp() * 1_000_000_000),
            rgba=bytes(buf),
        )
