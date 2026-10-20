"""Bounded, observation-only model for immutable View metadata snapshots.

The recorder accepts values, never Android View objects or callbacks. It has no
API for changing a hierarchy, submitting frames, or controlling a display.
Physical visibility remains unknown unless separately measured.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable


MAX_SAMPLES = 4096


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if any(type(value) is not int
               for value in (self.left, self.top, self.right, self.bottom)):
            raise ValueError("bounds must use integer coordinates")
        if any(abs(value) > 2_147_483_647
               for value in (self.left, self.top, self.right, self.bottom)):
            raise ValueError("bounds exceed the coordinate limit")
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("bounds must have positive dimensions")


class Visibility(str, Enum):
    VISIBLE = "visible"
    INVISIBLE = "invisible"
    GONE = "gone"
    UNKNOWN = "unknown"


class ImageScaleType(str, Enum):
    MATRIX = "MATRIX"
    FIT_XY = "FIT_XY"
    FIT_START = "FIT_START"
    FIT_CENTER = "FIT_CENTER"
    FIT_END = "FIT_END"
    CENTER = "CENTER"
    CENTER_CROP = "CENTER_CROP"
    CENTER_INSIDE = "CENTER_INSIDE"


class WindowLabel(str, Enum):
    """Finite caller-assigned labels; raw Android tokens cannot be represented."""

    WINDOW_0 = "window-0"
    WINDOW_1 = "window-1"
    WINDOW_2 = "window-2"
    WINDOW_3 = "window-3"
    WINDOW_4 = "window-4"
    WINDOW_5 = "window-5"
    WINDOW_6 = "window-6"
    WINDOW_7 = "window-7"


@dataclass(frozen=True)
class ViewMetadata:
    """Redacted values; never retains a View or raw window token.

    ``window_label`` must be an observer-assigned, non-sensitive label rather
    than the Android token or a stable device identifier.
    """

    label: str
    parent_chain: tuple[str, ...] | None
    attached: bool | None
    local_bounds: Bounds | None
    screen_location: tuple[int, int] | None
    global_visible_rect: Bounds | None
    visibility: Visibility = Visibility.UNKNOWN
    display_id: int | None = None
    window_label: WindowLabel | None = None

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("metadata label is required")
        if self.parent_chain is not None and type(self.parent_chain) is not tuple:
            raise ValueError("parent chain must be an immutable tuple")
        if self.parent_chain is not None and len(self.parent_chain) > 64:
            raise ValueError("parent chain exceeds the metadata bound")
        for label in (self.label, *(self.parent_chain or ())):
            if (type(label) is not str or not label or len(label) > 64
                    or not all(char.isalnum() or char in "._-" for char in label)):
                raise ValueError("labels must be short observer-assigned identifiers")
        if any(value is not None and type(value) is not Bounds
               for value in (self.local_bounds, self.global_visible_rect)):
            raise ValueError("bounds must use immutable Bounds values")
        if self.attached is not None and type(self.attached) is not bool:
            raise ValueError("attachment state must be true, false, or unknown")
        if not isinstance(self.visibility, Visibility):
            raise ValueError("visibility must use the Visibility enum")
        if self.screen_location is not None:
            if type(self.screen_location) is not tuple or len(self.screen_location) != 2 or any(
                    type(value) is not int or abs(value) > 2_147_483_647
                    for value in self.screen_location):
                raise ValueError("screen location must contain two integer coordinates")
        if self.display_id is not None and (
                type(self.display_id) is not int or not 0 <= self.display_id <= 2_147_483_647):
            raise ValueError("display id must be a non-negative integer or unknown")
        if self.window_label is not None and not isinstance(self.window_label, WindowLabel):
            raise ValueError("window identity must use a finite redacted label")


@dataclass(frozen=True)
class ViewSnapshot:
    sequence: int
    elapsed_ms: int
    main_root: ViewMetadata | None
    interrupt_root: ViewMetadata | None
    injected_view: ViewMetadata | None
    image_view: ViewMetadata | None
    source_frame_size: tuple[int, int] | None = None
    scale_type: ImageScaleType | None = None
    image_matrix: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or not 0 <= self.sequence <= 9_223_372_036_854_775_807:
            raise ValueError("sequence must be a non-negative integer")
        if type(self.elapsed_ms) is not int or not 0 <= self.elapsed_ms <= 9_223_372_036_854_775_807:
            raise ValueError("elapsed time must be a non-negative integer")
        if any(value is not None and type(value) is not ViewMetadata
               for value in (self.main_root, self.interrupt_root,
                             self.injected_view, self.image_view)):
            raise ValueError("snapshot nodes must be immutable ViewMetadata values")
        if self.source_frame_size is not None:
            if type(self.source_frame_size) is not tuple or len(self.source_frame_size) != 2:
                raise ValueError("source frame size must contain width and height")
            width, height = self.source_frame_size
            if any(type(value) is not int or value <= 0 or value > 2_147_483_647
                   for value in (width, height)):
                raise ValueError("source frame dimensions must be positive integers")
        if self.scale_type is not None and not isinstance(self.scale_type, ImageScaleType):
            raise ValueError("scale type must use the ImageScaleType enum")
        if self.image_matrix is not None:
            if type(self.image_matrix) is not tuple or len(self.image_matrix) != 9 or any(
                    type(value) not in (int, float) or abs(value) > 1_000_000_000_000
                    or not math.isfinite(value) for value in self.image_matrix):
                raise ValueError("image matrix must contain nine finite numeric coefficients")


class EventKind(str, Enum):
    ATTACHED = "attached"
    DETACHED = "detached"
    NODE_APPEARED = "node_appeared"
    NODE_DISAPPEARED = "node_disappeared"
    PARENT_CHAIN_CHANGED = "parent_chain_changed"
    VISIBILITY_CHANGED = "visibility_changed"
    GLOBAL_BOUNDS_CHANGED = "global_bounds_changed"
    LOCAL_BOUNDS_CHANGED = "local_bounds_changed"
    SCREEN_LOCATION_CHANGED = "screen_location_changed"
    DISPLAY_CHANGED = "display_changed"
    WINDOW_LABEL_CHANGED = "window_label_changed"
    SOURCE_FRAME_CHANGED = "source_frame_changed"
    SCALE_TYPE_CHANGED = "scale_type_changed"
    IMAGE_MATRIX_CHANGED = "image_matrix_changed"


@dataclass(frozen=True)
class ViewEvent:
    sequence: int
    target: str
    kind: EventKind
    before: object
    after: object


def compare_snapshots(previous: ViewSnapshot, current: ViewSnapshot) -> tuple[ViewEvent, ...]:
    """Report metadata changes without interpreting them as warning priority."""
    if current.sequence <= previous.sequence or current.elapsed_ms < previous.elapsed_ms:
        raise ValueError("snapshots must be strictly ordered")
    events: list[ViewEvent] = []
    pairs: Iterable[tuple[str, ViewMetadata | None, ViewMetadata | None]] = (
        (name, getattr(previous, name), getattr(current, name))
        for name in ("main_root", "interrupt_root", "injected_view", "image_view")
    )
    for name, before, after in pairs:
        if before is None or after is None:
            if before is not after:
                events.append(ViewEvent(current.sequence, name, EventKind.NODE_APPEARED
                                        if after is not None else EventKind.NODE_DISAPPEARED,
                                        before, after))
            continue
        if before.attached is False and after.attached is True:
            events.append(ViewEvent(current.sequence, name, EventKind.ATTACHED, False, True))
        elif before.attached is True and after.attached is False:
            events.append(ViewEvent(current.sequence, name, EventKind.DETACHED, True, False))
        if before.parent_chain != after.parent_chain:
            events.append(ViewEvent(current.sequence, name, EventKind.PARENT_CHAIN_CHANGED,
                                    before.parent_chain, after.parent_chain))
        if before.visibility != after.visibility:
            events.append(ViewEvent(current.sequence, name, EventKind.VISIBILITY_CHANGED,
                                    before.visibility, after.visibility))
        if before.global_visible_rect != after.global_visible_rect:
            events.append(ViewEvent(current.sequence, name, EventKind.GLOBAL_BOUNDS_CHANGED,
                                    before.global_visible_rect, after.global_visible_rect))
        for attr, kind in (("local_bounds", EventKind.LOCAL_BOUNDS_CHANGED),
                           ("screen_location", EventKind.SCREEN_LOCATION_CHANGED),
                           ("display_id", EventKind.DISPLAY_CHANGED),
                           ("window_label", EventKind.WINDOW_LABEL_CHANGED)):
            old, new = getattr(before, attr), getattr(after, attr)
            if old != new:
                events.append(ViewEvent(current.sequence, name, kind, old, new))
    for attr, kind in (("source_frame_size", EventKind.SOURCE_FRAME_CHANGED),
                       ("scale_type", EventKind.SCALE_TYPE_CHANGED),
                       ("image_matrix", EventKind.IMAGE_MATRIX_CHANGED)):
        old, new = getattr(previous, attr), getattr(current, attr)
        if old != new:
            events.append(ViewEvent(current.sequence, "image_view", kind, old, new))
    return tuple(events)


class ObservationRecorder:
    """In-memory recorder with fixed capacity and explicit stop semantics."""

    def __init__(self, max_samples: int = 512) -> None:
        if (isinstance(max_samples, bool) or not isinstance(max_samples, int)
                or not 1 <= max_samples <= MAX_SAMPLES):
            raise ValueError(f"max_samples must be between 1 and {MAX_SAMPLES}")
        self._max_samples = max_samples
        self._samples: list[ViewSnapshot] = []
        self._events: list[ViewEvent] = []
        self._closed = False
        self._capacity_reached = False

    @property
    def samples(self) -> tuple[ViewSnapshot, ...]:
        return tuple(self._samples)

    @property
    def events(self) -> tuple[ViewEvent, ...]:
        return tuple(self._events)

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def capacity_reached(self) -> bool:
        return self._capacity_reached

    def record(self, snapshot: ViewSnapshot) -> bool:
        """Append a metadata-only sample; return False after stop/capacity."""
        if self._closed or self._capacity_reached:
            return False
        if type(snapshot) is not ViewSnapshot:
            raise TypeError("recorder accepts immutable ViewSnapshot values only")
        if len(self._samples) >= self._max_samples:
            self._capacity_reached = True
            return False
        if self._samples:
            prior = self._samples[-1]
            new_events = compare_snapshots(prior, snapshot)
            self._events.extend(new_events)
        self._samples.append(snapshot)
        if len(self._samples) == self._max_samples:
            self._capacity_reached = True
        return True

    def stop(self) -> None:
        """Close collection; retained immutable records remain readable."""
        self._closed = True
