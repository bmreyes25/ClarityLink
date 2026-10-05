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
    """Tk host window for clear decoded frames; main-thread use only.

    Keeps a centered, aspect-preserving image inside an 800x480 canvas by
    integer subsampling oversized PNGs. Target Honda display is unrelated.
    """

    def __init__(self, width: int = 800, height: int = 480) -> None:
        super().__init__()
        if width < 1 or height < 1 or width > 4096 or height > 4096:
            raise DisplayError("invalid_host_window_size")
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.title("ClarityLink Type111 host laboratory")
            self.canvas = tk.Canvas(self.root, width=width, height=height, bg="black")
            self.canvas.pack()
            self.root.update()
        except Exception as exc:
            raise DisplayError("host_gui_unavailable") from exc
        self.width, self.height = width, height
        self._image = None
        self._generation: int | None = None

    def begin_generation(self, generation: int) -> None:
        if generation < 1:
            raise DisplayError("invalid_display_generation")
        self.clear()
        self._generation = generation

    def show(self, frame: DecodedFrame) -> None:
        if self._generation != frame.generation:
            raise DisplayError("stale_display_frame")
        import base64
        try:
            import tkinter as tk
            picture = tk.PhotoImage(data=base64.b64encode(frame.png).decode("ascii"))
            factor = max(1, (picture.width() + self.width - 1) // self.width,
                         (picture.height() + self.height - 1) // self.height)
            if factor > 1:
                picture = picture.subsample(factor)
            self.canvas.delete("frame")
            self.canvas.create_image(self.width // 2, self.height // 2, image=picture, tags="frame")
            self._image = picture
            self.root.update()
        except Exception as exc:
            raise DisplayError("host_window_render_failed") from exc
        super().show(frame)

    def clear(self) -> None:
        if hasattr(self, "canvas"):
            self.canvas.delete("frame")
            self._image = None
            self.root.update()
        self._generation = None
        super().clear()

    def close(self) -> None:
        self.clear()
        self.root.destroy()
