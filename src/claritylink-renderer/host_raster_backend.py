"""Host-only raster surface for exercising the Display 1 frame boundary.

This is a real in-memory RGBA rasterizer with an explicitly modeled host View
and Surface lifecycle. It does not use Android Surface/SurfaceFlinger, a Honda
display, or a physical cluster. Geometry is supplied by the test host.
"""
from __future__ import annotations

from dataclasses import dataclass

from model import DecodedFrame, DisplayTarget, PIXEL_FORMAT


DISPLAY1_WIDTH = 800
DISPLAY1_HEIGHT = 480


class HostBoundaryError(RuntimeError):
    pass


class StaleHostLease(HostBoundaryError):
    pass


@dataclass(frozen=True)
class ViewBounds:
    """Synthetic View bounds; partially off-canvas bounds are clipped by Surface."""

    left: int
    top: int
    width: int
    height: int

    def validate(self) -> None:
        if (any(type(value) is not int for value in (self.left, self.top, self.width, self.height))
                or self.width <= 0 or self.height <= 0
                or abs(self.left) > DISPLAY1_WIDTH * 4
                or abs(self.top) > DISPLAY1_HEIGHT * 4
                or self.width > DISPLAY1_WIDTH * 4 or self.height > DISPLAY1_HEIGHT * 4):
            raise HostBoundaryError("invalid synthetic View bounds")


class RasterSurface:
    """Bounded RGBA layer with nearest-neighbor crop/rotation/scaling and clipping."""

    def __init__(self, width: int = DISPLAY1_WIDTH, height: int = DISPLAY1_HEIGHT) -> None:
        if (type(width) is not int or type(height) is not int or width != DISPLAY1_WIDTH
                or height != DISPLAY1_HEIGHT):
            raise HostBoundaryError("prototype surface must model logical Display 1 at 800x480")
        self.width, self.height = width, height
        self._pixels = bytearray(width * height * 4)
        self.destroyed = False

    def draw(self, frame: DecodedFrame, bounds: ViewBounds) -> None:
        if self.destroyed:
            raise HostBoundaryError("Surface is destroyed")
        bounds.validate()
        frame.validate(require_cpu=True)
        if frame.pixel_format != PIXEL_FORMAT:
            raise HostBoundaryError("unsupported frame pixel format")

        crop_left, crop_top, crop_right, crop_bottom = frame.crop or (
            0, 0, frame.width, frame.height)
        crop_width, crop_height = crop_right - crop_left, crop_bottom - crop_top
        rotated_width, rotated_height = ((crop_height, crop_width)
                                         if frame.rotation_degrees in (90, 270)
                                         else (crop_width, crop_height))
        x0, y0 = max(0, bounds.left), max(0, bounds.top)
        x1 = min(self.width, bounds.left + bounds.width)
        y1 = min(self.height, bounds.top + bounds.height)
        for target_y in range(y0, y1):
            view_y = target_y - bounds.top
            rotated_y = min(rotated_height - 1, view_y * rotated_height // bounds.height)
            for target_x in range(x0, x1):
                view_x = target_x - bounds.left
                rotated_x = min(rotated_width - 1, view_x * rotated_width // bounds.width)
                if frame.rotation_degrees == 90:
                    source_x = crop_left + rotated_y
                    source_y = crop_top + crop_height - 1 - rotated_x
                elif frame.rotation_degrees == 180:
                    source_x = crop_left + crop_width - 1 - rotated_x
                    source_y = crop_top + crop_height - 1 - rotated_y
                elif frame.rotation_degrees == 270:
                    source_x = crop_left + crop_width - 1 - rotated_y
                    source_y = crop_top + rotated_x
                else:
                    source_x = crop_left + rotated_x
                    source_y = crop_top + rotated_y
                source_offset = source_y * frame.row_stride + source_x * 4
                target_offset = (target_y * self.width + target_x) * 4
                self._pixels[target_offset:target_offset + 4] = frame.rgba[source_offset:source_offset + 4]

    def clear(self) -> None:
        if not self.destroyed:
            self._pixels[:] = bytes(len(self._pixels))

    def destroy(self) -> None:
        if self.destroyed:
            return
        self.clear()
        self.destroyed = True

    def pixel(self, x: int, y: int) -> tuple[int, int, int, int]:
        if self.destroyed or not (0 <= x < self.width and 0 <= y < self.height):
            raise HostBoundaryError("pixel unavailable")
        offset = (y * self.width + x) * 4
        return tuple(self._pixels[offset:offset + 4])  # type: ignore[return-value]

    def snapshot(self) -> bytes:
        if self.destroyed:
            raise HostBoundaryError("Surface is destroyed")
        return bytes(self._pixels)


@dataclass(eq=False, frozen=True)
class HostViewLease:
    generation: int
    display_id: int


class _HostView:
    def __init__(self, lease: HostViewLease, surface: RasterSurface, bounds: ViewBounds) -> None:
        self.lease = lease
        self.surface = surface
        self.bounds = bounds
        self.attached = True


class RasterDisplay1HostBackend:
    """Fail-closed in-memory host equivalent for offline renderer experiments.

    The API mirrors the existing renderer's attach/submit/clear/close boundary,
    while lifecycle events revoke a unique per-attachment lease. Reselect and
    host restoration do not reattach or replay prior frames.
    """

    def __init__(self, bounds: ViewBounds = ViewBounds(0, 0, 584, 191)) -> None:
        bounds.validate()
        self.bounds = bounds
        self.navigation_selected = True
        self.parent_session_active = True
        self.host_alive = True
        self._view: _HostView | None = None
        self._highest_generation = 0
        self._last_timestamp = -1
        self.created_surfaces = 0
        self.destroyed_surfaces = 0
        self.accepted_frames = 0

    @property
    def attached(self) -> bool:
        return self._view is not None and self._view.attached

    @property
    def surface(self) -> RasterSurface | None:
        return self._view.surface if self.attached else None

    @property
    def active_lease(self) -> HostViewLease | None:
        return self._view.lease if self.attached else None

    def attach(self, target: DisplayTarget) -> HostViewLease:
        target.validate()
        if target.display_id != 1 or (target.width, target.height) != (800, 480):
            raise HostBoundaryError("only the modeled Display 1 target is admitted")
        if not self.host_alive or not self.parent_session_active or not self.navigation_selected:
            raise HostBoundaryError("host, parent session, and Navigation selection are required")
        if self.attached:
            raise HostBoundaryError("host View is already attached")
        self._highest_generation += 1
        lease = HostViewLease(self._highest_generation, target.display_id)
        surface = RasterSurface(target.width, target.height)
        self._view = _HostView(lease, surface, self.bounds)
        self._last_timestamp = -1
        self.created_surfaces += 1
        return lease

    def submit(self, frame: DecodedFrame, lease: HostViewLease) -> None:
        view = self._view
        if view is None or lease is not view.lease:
            raise StaleHostLease("frame does not hold the active host View lease")
        if not self.navigation_selected or not self.parent_session_active or not self.host_alive:
            raise StaleHostLease("host boundary is not in an admitting state")
        frame.validate(require_cpu=True)
        if frame.presentation_time_ns <= self._last_timestamp:
            raise HostBoundaryError("frame timestamp must increase within a lease")
        view.surface.draw(frame, view.bounds)
        self._last_timestamp = frame.presentation_time_ns
        self.accepted_frames += 1

    def clear(self, lease: HostViewLease) -> None:
        view = self._view
        if view is None or lease is not view.lease:
            raise StaleHostLease("clear requires the active host View lease")
        view.surface.clear()
        self._last_timestamp = -1

    def close(self, lease: HostViewLease | None = None) -> None:
        if self._view is None:
            return
        if lease is not None and lease is not self._view.lease:
            raise StaleHostLease("close requires the active host View lease")
        self._detach()

    def set_navigation_selected(self, selected: bool) -> None:
        self.navigation_selected = bool(selected)
        if not self.navigation_selected:
            self._detach()

    def terminate_parent_session(self) -> None:
        self.parent_session_active = False
        self._detach()

    def host_lost(self) -> None:
        self.host_alive = False
        self._detach()

    def host_restored(self) -> None:
        self.host_alive = True
        # A new attach and lease are required before any frame can return.

    def begin_parent_session(self) -> None:
        if self.parent_session_active:
            raise HostBoundaryError("parent session is already active")
        self.parent_session_active = True
        # Existing Navigation selection is a precondition, not new authority.

    def _detach(self) -> None:
        view, self._view = self._view, None
        if view is None:
            return
        view.attached = False
        view.surface.destroy()
        self.destroyed_surfaces += 1
        self._last_timestamp = -1


def synthetic_type111_rgb24_to_rgba(decoded: object) -> DecodedFrame:
    """Adapt the existing Type111 lab RGB24 frame into the renderer's RGBA contract."""
    if getattr(decoded, "stream_type", None) != 111:
        raise HostBoundaryError("only the laboratory Type111 secondary stream is accepted")
    provenance = getattr(getattr(decoded, "provenance", None), "value", None)
    if provenance != "SYNTHETIC_LAB_CONTENT":
        raise HostBoundaryError("bench adapter only accepts explicitly synthetic Type111 pixels")
    width, height, stride, pixels = (getattr(decoded, name, None) for name in
                                     ("width", "height", "stride", "pixels"))
    if (type(width) is not int or type(height) is not int or type(stride) is not int
            or stride != width * 3 or not isinstance(pixels, bytes)
            or len(pixels) != stride * height):
        raise HostBoundaryError("invalid decoded Type111 RGB24 frame")
    rgba = bytearray(width * height * 4)
    for source in range(0, len(pixels), 3):
        target = source // 3 * 4
        rgba[target:target + 3] = pixels[source:source + 3]
        rgba[target + 3] = 255
    frame = DecodedFrame(width, height, PIXEL_FORMAT, width * 4,
                         getattr(decoded, "timestamp", -1), rgba=bytes(rgba))
    frame.validate(require_cpu=True)
    return frame
