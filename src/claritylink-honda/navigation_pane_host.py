"""Simulated Navigation-pane host with an explicit page layer (CL-HONDA-111-01).

Original, offline, synthetic model of the *layers* the Navigation-pane contract
(``research/honda/cl-honda-111-01-navigation-pane-contract.md``) keeps apart:

  display          -- the external display exists and is valid
  host windows     -- a main layer and a top-most interrupt layer, composed by
                      the existing ``SimulatedClusterHost``
  selectable page  -- whether the driver-selected Navigation page is showing
  viewport         -- an explicit, caller-provided destination rectangle
  lease            -- a revocable, generation-bound right to present in the pane

Nothing here reproduces a Honda identifier, constant, geometry or window
parameter, performs I/O, or reaches a vehicle. It models ClarityLink's own
behavior and proves nothing about the real Honda display host.

Safety posture (do not relax):
  * A pane lease needs ALL of: valid display, Navigation page selected, no
    interrupt, a usable viewport, and a strictly newer generation than any
    lease this host has ever granted.
  * Any of: page deselected, interrupt, display loss, host close, or a newer
    lease revokes the current lease immediately and synchronously. Revocation
    can never fail and never depends on content rendering.
  * Leaving the pane or clearing an interrupt NEVER re-exposes old content. A
    new lease with a newer generation is always required.
  * A viewport must say where it came from. A layout-local candidate (for
    example a third-party app's own ImageView size) or an unknown origin is
    refused; it is never treated as a physical safe area.
  * Unknown or malformed input denies.
"""
from __future__ import annotations

import sys
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import simulated_cluster_host as sch  # noqa: E402

# Bounds mirror the API17 CPU frame contract (DecodedFrame.java) so the two sides
# accept and reject the same frames.
MAX_WIDTH = 3840
MAX_HEIGHT = 2160
MAX_FRAME_BYTES = 4 * 1024 * 1024
MAX_REVOKE_CALLBACKS = 16


class ViewportSource(str, Enum):
    SYNTHETIC_TEST = "SYNTHETIC_TEST"
    AUTHORITATIVE_MEASURED = "AUTHORITATIVE_MEASURED"   # reserved: no such measurement exists yet
    LAYOUT_LOCAL_CANDIDATE = "LAYOUT_LOCAL_CANDIDATE"   # never admissible
    UNKNOWN = "UNKNOWN"                                 # never admissible


_ADMISSIBLE_SOURCES = (ViewportSource.SYNTHETIC_TEST, ViewportSource.AUTHORITATIVE_MEASURED)


@dataclass(frozen=True)
class Viewport:
    x: int
    y: int
    width: int
    height: int
    source: ViewportSource = ViewportSource.UNKNOWN

    def __post_init__(self) -> None:
        for name in ("x", "y", "width", "height"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int):
                raise ValueError(f"viewport {name} must be an int")
        if self.x < 0 or self.y < 0 or self.width < 1 or self.height < 1:
            raise ValueError("viewport must have a non-negative origin and positive size")
        if not isinstance(self.source, ViewportSource):
            raise ValueError("viewport source must be a ViewportSource")


class ContentClass(str, Enum):
    """Role-level class of what the host reports as currently selected. The
    real host uses numeric content identifiers; none are reproduced here."""
    NAVIGATION = "NAVIGATION"
    WARNING = "WARNING"
    OTHER = "OTHER"
    NONE = "NONE"


class ContentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class PixelFormat(str, Enum):
    RGBA_8888 = "RGBA_8888"   # byte order R, G, B, A, as in the API17 CPU frame

    @property
    def bytes_per_pixel(self) -> int:
        return 4


class FrameStorage(str, Enum):
    CPU_BUFFER = "CPU_BUFFER"
    SURFACE = "SURFACE"   # accepted by the type, refused by this host (no Surface owner exists)


@dataclass
class DecodedFrame:
    """One decoded Type111 frame handed toward the pane.

    ``release`` is called exactly once, whatever happens to the frame, so the
    producer can recycle its buffer. The payload is held by reference.
    """
    stream_connection_id: int
    parent_generation: int
    stream_generation: int
    config_generation: int
    sequence: int
    presentation_time_ns: int
    width: int
    height: int
    stride: int
    pixel_format: PixelFormat = PixelFormat.RGBA_8888
    storage: FrameStorage = FrameStorage.CPU_BUFFER
    crop: tuple[int, int, int, int] | None = None       # left, top, right, bottom (right/bottom exclusive)
    rotation: int = 0                                    # clockwise degrees: 0, 90, 180, 270
    payload: Any = field(default=None, repr=False)
    release_callback: Callable[[], None] | None = field(default=None, repr=False)
    _released: bool = field(default=False, init=False, repr=False)

    def effective_size(self) -> tuple[int, int]:
        w, h = ((self.crop[2] - self.crop[0], self.crop[3] - self.crop[1])
                if self.crop else (self.width, self.height))
        return (h, w) if self.rotation in (90, 270) else (w, h)

    def validate(self) -> str | None:
        """Return a reason code if the frame is malformed, else ``None``."""
        for name in ("stream_connection_id", "parent_generation", "stream_generation",
                     "config_generation", "sequence", "presentation_time_ns",
                     "width", "height", "stride", "rotation"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                return "malformed_field"
        if self.stream_connection_id < 1 or self.parent_generation < 1 or self.stream_generation < 1:
            return "malformed_identity"
        if not isinstance(self.pixel_format, PixelFormat) or not isinstance(self.storage, FrameStorage):
            return "malformed_format"
        if not (1 <= self.width <= MAX_WIDTH and 1 <= self.height <= MAX_HEIGHT):
            return "invalid_dimensions"
        if self.rotation not in (0, 90, 180, 270):
            return "invalid_rotation"
        if self.crop is not None:
            if (not isinstance(self.crop, tuple) or len(self.crop) != 4 or
                    any(isinstance(c, bool) or not isinstance(c, int) for c in self.crop)):
                return "invalid_crop"
            left, top, right, bottom = self.crop
            if (left < 0 or top < 0 or left >= right or top >= bottom or
                    right > self.width or bottom > self.height):
                return "invalid_crop"
        if self.storage is FrameStorage.CPU_BUFFER:
            bpp = self.pixel_format.bytes_per_pixel
            if self.stride < self.width * bpp:
                return "invalid_stride"
            need = self.stride * self.height
            if need > MAX_FRAME_BYTES:
                return "frame_too_large"
            if not isinstance(self.payload, (bytes, bytearray, memoryview)) or len(self.payload) < need:
                return "short_payload"
        return None

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        cb, self.release_callback = self.release_callback, None
        if cb is not None:
            try:
                cb()
            except Exception:
                pass   # a producer's release failure must not break teardown


def fit_rect(src_w: int, src_h: int, viewport: Viewport) -> tuple[int, int, int, int]:
    """Uniform scale-to-fit, centered in the viewport. Pure arithmetic."""
    if src_w < 1 or src_h < 1:
        raise ValueError("source size must be positive")
    scale_num, scale_den = (viewport.width, src_w) if viewport.width * src_h <= viewport.height * src_w \
        else (viewport.height, src_h)
    dw = max(1, (src_w * scale_num) // scale_den)
    dh = max(1, (src_h * scale_num) // scale_den)
    return (viewport.x + (viewport.width - dw) // 2,
            viewport.y + (viewport.height - dh) // 2, dw, dh)


@dataclass(frozen=True)
class PaneOwner:
    stream_connection_id: int
    parent_generation: int
    pane_generation: int


class AcquireStatus(str, Enum):
    GRANTED = "GRANTED"
    REPLACED = "REPLACED"
    DENIED_CLOSED = "DENIED_CLOSED"
    DENIED_NO_DISPLAY = "DENIED_NO_DISPLAY"
    DENIED_INTERRUPTED = "DENIED_INTERRUPTED"
    DENIED_PAGE_NOT_SELECTED = "DENIED_PAGE_NOT_SELECTED"
    DENIED_NO_VIEWPORT = "DENIED_NO_VIEWPORT"
    DENIED_STALE_GENERATION = "DENIED_STALE_GENERATION"
    DENIED_NOT_ADMISSIBLE = "DENIED_NOT_ADMISSIBLE"


class PresentStatus(str, Enum):
    PRESENTED = "PRESENTED"
    DENIED_LEASE_INVALID = "DENIED_LEASE_INVALID"
    DENIED_IDENTITY_MISMATCH = "DENIED_IDENTITY_MISMATCH"
    DENIED_STALE_SEQUENCE = "DENIED_STALE_SEQUENCE"
    DENIED_MALFORMED = "DENIED_MALFORMED"
    DENIED_UNSUPPORTED_STORAGE = "DENIED_UNSUPPORTED_STORAGE"
    DENIED_GEOMETRY = "DENIED_GEOMETRY"


@dataclass(frozen=True)
class AcquireResult:
    status: AcquireStatus
    lease: "PaneLease | None" = None

    @property
    def granted(self) -> bool:
        return self.lease is not None


@dataclass(frozen=True)
class PresentResult:
    status: PresentStatus
    reason: str = ""
    destination: tuple[int, int, int, int] | None = None

    @property
    def presented(self) -> bool:
        return self.status is PresentStatus.PRESENTED


class PaneHost(Protocol):
    """What the bridge needs from any pane host, simulated or not."""

    def next_generation(self) -> int: ...
    def acquire(self, owner: PaneOwner) -> AcquireResult: ...
    def present(self, lease: "PaneLease", frame: DecodedFrame) -> PresentResult: ...
    def withdraw(self, lease: "PaneLease") -> None: ...


class PaneLease:
    """Revocable right to present in the pane. Created only by a host."""

    def __init__(self, host: "NavigationPaneHost", owner: PaneOwner) -> None:
        self._host = host
        self._owner = owner
        self._revoked: str | None = None
        self._callbacks: list[Callable[[str], None]] = []
        self.last_sequence: int | None = None

    @property
    def owner(self) -> PaneOwner:
        return self._owner

    @property
    def valid(self) -> bool:
        return self._revoked is None and self._host._lease is self

    @property
    def revoked_reason(self) -> str | None:
        return self._revoked

    def __repr__(self) -> str:
        return f"PaneLease(valid={self.valid}, <redacted>)"

    def add_revoke_callback(self, callback: Callable[[str], None]) -> None:
        run_now = None
        with self._host._lock:
            if self._revoked is not None:
                run_now = self._revoked
            else:
                if len(self._callbacks) >= MAX_REVOKE_CALLBACKS:
                    raise ValueError("too_many_revoke_callbacks")
                self._callbacks.append(callback)
        if run_now is not None:
            _run_contained(callback, run_now)

    def _revoke(self, reason: str) -> list[Callable[[str], None]]:
        if self._revoked is not None:
            return []
        self._revoked = reason
        callbacks, self._callbacks = self._callbacks, []
        return callbacks


def _run_contained(callback: Callable[[str], None], reason: str) -> None:
    try:
        callback(reason)
    except Exception:
        pass


@dataclass
class PaneStats:
    leases_granted: int = 0
    leases_replaced: int = 0
    leases_denied: int = 0
    leases_revoked: int = 0
    frames_presented: int = 0
    frames_denied: int = 0
    page_deselects: int = 0
    page_selects: int = 0
    viewports_rejected: int = 0


class NavigationPaneHost:
    """Display + windows + page + viewport + lease, all synthetic."""

    def __init__(self) -> None:
        self._cluster = sch.SimulatedClusterHost()
        self._page_selected = False
        self._viewport: Viewport | None = None
        self._lease: PaneLease | None = None
        self._high_water = 0
        self._presented: tuple[int, tuple[int, int, int, int], int] | None = None
        self._closed = False
        self._lock = threading.RLock()
        self._observed: tuple[ContentClass, ContentStatus, int] | None = None
        self._interrupt_from_observation = False
        self.stats = PaneStats()

    # ---- read-only ----
    @property
    def synthetic(self) -> bool:
        return True

    def safe_for_honda(self) -> bool:
        return False

    @property
    def display_available(self) -> bool:
        return self._cluster.display_available

    @property
    def page_selected(self) -> bool:
        return self._page_selected

    @property
    def interrupt_active(self) -> bool:
        return self._cluster.interrupt_active

    @property
    def viewport(self) -> Viewport | None:
        return self._viewport

    @property
    def lease(self) -> PaneLease | None:
        return self._lease if self._lease is not None and self._lease.valid else None

    @property
    def presented(self) -> tuple[int, tuple[int, int, int, int], int] | None:
        """(sequence, destination rect, pane generation) of what is on the pane."""
        return self._presented

    @property
    def main_layer_occupied(self) -> bool:
        """Whether the simulated host's main layer still has a custom owner.
        Every revocation clears it, independently of lease bookkeeping."""
        return self._cluster.main_owner is not None

    @property
    def custom_content_visible(self) -> bool:
        with self._lock:
            return (self._presented is not None and self._lease is not None and self._lease.valid
                    and self._page_selected and self._cluster.main_presentable())

    @property
    def factory_content_visible(self) -> bool:
        """True whenever the display exists and no custom content is shown. The
        factory warning layer is separate and never owned here."""
        return self.display_available and not self.custom_content_visible

    # ---- display lifecycle ----
    def connect_display(self) -> None:
        self._end_lease(lambda: self._cluster.connect_display(), "display_connected_rebuild")

    def lose_display(self) -> None:
        self._end_lease(lambda: self._cluster.lose_display(), "display_lost")

    def begin_restore(self) -> None:
        self._cluster.begin_restore()

    def complete_restore(self, *, display_valid: bool) -> bool:
        outcome: list[bool] = []
        self._end_lease(lambda: outcome.append(
            self._cluster.complete_restore(display_valid=display_valid)), "display_restored_rebuild")
        return bool(outcome and outcome[0])

    def close(self) -> None:
        self._end_lease(lambda: self._cluster.close(), "host_closed")
        self._closed = True

    # ---- page layer ----
    def select_navigation_page(self, selected: bool) -> None:
        """The driver changed the selectable page. Leaving Navigation revokes the
        lease; returning to it grants nothing by itself."""
        if not isinstance(selected, bool):
            raise ValueError("selected must be a bool")
        with self._lock:
            was = self._page_selected
            self._page_selected = selected
            if selected and not was:
                self.stats.page_selects += 1
        if was and not selected:
            self.stats.page_deselects += 1
            self._end_lease(lambda: None, "page_deselected")

    def observe_contents(self, content: ContentClass, status: ContentStatus, *, tick: int) -> bool:
        """Drive the page and interrupt layers from the host's reported selection.

        Fail-closed mapping: only ``NAVIGATION`` + ``ACTIVE`` selects the page. A
        warning that is ACTIVE raises the interrupt layer; a warning leaving does
        not re-select anything. Any other class, any non-ACTIVE navigation
        status, and any UNKNOWN status deselect the page: an unreadable state is
        never read as "still ours". An observation older than the newest one seen
        is ignored. Returns whether it was applied.
        """
        if not isinstance(content, ContentClass) or not isinstance(status, ContentStatus):
            raise ValueError("content and status must be enum members")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative int")
        with self._lock:
            if self._observed is not None and tick < self._observed[2]:
                return False
            self._observed = (content, status, tick)
        if content is ContentClass.WARNING and status is ContentStatus.ACTIVE:
            self._interrupt_from_observation = True
            self.activate_interrupt()
            self.select_navigation_page(False)
            return True
        if self._interrupt_from_observation:
            self._interrupt_from_observation = False
            self.clear_interrupt()
        self.select_navigation_page(content is ContentClass.NAVIGATION and status is ContentStatus.ACTIVE)
        return True

    def expire_observation(self, now_tick: int, *, max_age: int) -> bool:
        """Deselect the page when the host has not reported for ``max_age`` ticks
        (or has never reported). A silent host is not evidence of anything."""
        if (isinstance(now_tick, bool) or not isinstance(now_tick, int) or now_tick < 0 or
                isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 0):
            raise ValueError("ticks must be non-negative ints")
        with self._lock:
            stale = self._observed is None or now_tick - self._observed[2] > max_age
        if stale and self._page_selected:
            self.select_navigation_page(False)
        return stale

    def set_viewport(self, viewport: Viewport | None) -> bool:
        """Set the destination rectangle. Only an admissible source is accepted;
        replacing or clearing it revokes any lease because geometry changed."""
        if viewport is not None:
            if not isinstance(viewport, Viewport) or viewport.source not in _ADMISSIBLE_SOURCES:
                self.stats.viewports_rejected += 1
                return False
        with self._lock:
            changed = viewport != self._viewport
            self._viewport = viewport
        if changed:
            self._end_lease(lambda: None, "viewport_changed")
        return True

    # ---- interrupt layer (independent, always wins) ----
    def activate_interrupt(self) -> None:
        self._end_lease(lambda: self._cluster.activate_interrupt(), "interrupt")

    def clear_interrupt(self) -> None:
        with self._lock:
            self._cluster.clear_interrupt()   # restores NOTHING of ours

    # ---- lease ----
    def next_generation(self) -> int:
        """The smallest pane generation this host would currently accept. A fresh,
        legitimate holder asks for it; a revoked lease can never be revived,
        because its object is dead whatever number it carries."""
        with self._lock:
            return self._high_water + 1

    def acquire(self, owner: PaneOwner) -> AcquireResult:
        if not isinstance(owner, PaneOwner):
            raise ValueError("owner must be a PaneOwner")
        for value in (owner.stream_connection_id, owner.parent_generation, owner.pane_generation):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("owner fields must be positive ints")
        with self._lock:
            denied = self._deny_reason(owner)
            if denied is not None:
                self.stats.leases_denied += 1
                return AcquireResult(denied)
            previous = self._lease if self._lease is not None and self._lease.valid else None
            result = self._cluster.present_main(
                session_id=owner.parent_generation, generation=owner.pane_generation,
                content="PANE")
            if result in (sch.PresentResult.REJECTED_STALE_GENERATION,):
                self.stats.leases_denied += 1
                return AcquireResult(AcquireStatus.DENIED_STALE_GENERATION)
            if result not in (sch.PresentResult.PRESENTED, sch.PresentResult.REPLACED):
                self.stats.leases_denied += 1
                return AcquireResult(AcquireStatus.DENIED_NO_DISPLAY)
            callbacks = previous._revoke("replaced") if previous is not None else []
            self._high_water = owner.pane_generation
            lease = PaneLease(self, owner)
            self._lease = lease
            self._presented = None
            self.stats.leases_granted += 1
            if previous is not None:
                self.stats.leases_replaced += 1
                self.stats.leases_revoked += 1
        for cb in callbacks:
            _run_contained(cb, "replaced")
        return AcquireResult(AcquireStatus.REPLACED if previous is not None else AcquireStatus.GRANTED, lease)

    def _deny_reason(self, owner: PaneOwner) -> AcquireStatus | None:
        if self._closed:
            return AcquireStatus.DENIED_CLOSED
        if not self._cluster.display_available:
            return AcquireStatus.DENIED_NO_DISPLAY
        if self._cluster.interrupt_active:
            return AcquireStatus.DENIED_INTERRUPTED
        if not self._page_selected:
            return AcquireStatus.DENIED_PAGE_NOT_SELECTED
        if self._viewport is None:
            return AcquireStatus.DENIED_NO_VIEWPORT
        if self._viewport.source not in _ADMISSIBLE_SOURCES:
            return AcquireStatus.DENIED_NOT_ADMISSIBLE
        if owner.pane_generation <= self._high_water:
            return AcquireStatus.DENIED_STALE_GENERATION
        return None

    def present(self, lease: PaneLease, frame: DecodedFrame) -> PresentResult:
        with self._lock:
            result = self._present_locked(lease, frame)
            if result.presented:
                self.stats.frames_presented += 1
            else:
                self.stats.frames_denied += 1
            return result

    def _present_locked(self, lease: PaneLease, frame: DecodedFrame) -> PresentResult:
        if not isinstance(lease, PaneLease) or lease._host is not self or not lease.valid:
            return PresentResult(PresentStatus.DENIED_LEASE_INVALID, "lease_invalid")
        if not self._page_selected or not self._cluster.main_presentable():
            return PresentResult(PresentStatus.DENIED_LEASE_INVALID, "pane_not_presentable")
        if not isinstance(frame, DecodedFrame):
            return PresentResult(PresentStatus.DENIED_MALFORMED, "not_a_frame")
        problem = frame.validate()
        if problem is not None:
            return PresentResult(PresentStatus.DENIED_MALFORMED, problem)
        if frame.storage is not FrameStorage.CPU_BUFFER:
            return PresentResult(PresentStatus.DENIED_UNSUPPORTED_STORAGE, "surface_storage_unsupported")
        owner = lease.owner
        if (frame.stream_connection_id != owner.stream_connection_id or
                frame.parent_generation != owner.parent_generation):
            return PresentResult(PresentStatus.DENIED_IDENTITY_MISMATCH, "frame_identity_mismatch")
        if lease.last_sequence is not None and frame.sequence <= lease.last_sequence:
            return PresentResult(PresentStatus.DENIED_STALE_SEQUENCE, "stale_or_duplicate_sequence")
        viewport = self._viewport
        if viewport is None or viewport.source not in _ADMISSIBLE_SOURCES:
            return PresentResult(PresentStatus.DENIED_GEOMETRY, "viewport_unavailable")
        ew, eh = frame.effective_size()
        if ew < 1 or eh < 1:
            return PresentResult(PresentStatus.DENIED_GEOMETRY, "empty_effective_size")
        destination = fit_rect(ew, eh, viewport)
        lease.last_sequence = frame.sequence
        self._presented = (frame.sequence, destination, owner.pane_generation)
        return PresentResult(PresentStatus.PRESENTED, "", destination)

    def withdraw(self, lease: PaneLease) -> None:
        """Remove our content. Always allowed; a stale lease is a no-op."""
        if isinstance(lease, PaneLease) and lease._host is self and lease.valid:
            self._end_lease(lambda: self._cluster.withdraw_main(), "withdrawn")

    # ---- internals ----
    def _end_lease(self, host_action: Callable[[], None], reason: str) -> None:
        with self._lock:
            host_action()
            self._cluster.withdraw_main()   # always allowed; never re-exposes anything
            callbacks = self._revoke_locked(reason)
        for cb in callbacks:
            _run_contained(cb, reason)

    def _revoke_locked(self, reason: str) -> list[Callable[[str], None]]:
        lease, self._lease = self._lease, None
        self._presented = None
        if lease is None or lease.revoked_reason is not None:
            return []
        self.stats.leases_revoked += 1
        return lease._revoke(reason)
