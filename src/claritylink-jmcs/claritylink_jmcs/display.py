"""Host-only display outputs; no Android or Honda Display 1 access."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .decoder import DecodedFrame


class DisplayError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class Display1Output(Protocol):
    def show(self, frame: DecodedFrame) -> None: ...
    def clear(self) -> None: ...


class NullDisplay:
    def __init__(self) -> None:
        self.frames = 0
        self.current: DecodedFrame | None = None

    def show(self, frame: DecodedFrame) -> None:
        self.frames += 1
        self.current = frame

    def clear(self) -> None:
        self.current = None


class FrameDumpDisplay(NullDisplay):
    """Writes only a selected local PNG path, never a device/display node."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path.resolve()
        if self.path.suffix.lower() != ".png" or str(self.path).startswith("/dev/"):
            raise DisplayError("invalid_host_output")
        if self.path.exists():
            raise DisplayError("host_output_already_exists")
        self._owned = False

    def show(self, frame: DecodedFrame) -> None:
        super().show(frame)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._owned = True
        self.path.write_bytes(frame.png)

    def clear(self) -> None:
        super().clear()
        if self._owned and self.path.exists():
            self.path.unlink()
        self._owned = False


class HostWindowDisplay(NullDisplay):
    """In-memory host frame handoff for a separate GUI presenter.

    The integration test uses FrameDumpDisplay. No GUI framework is assumed.
    """
