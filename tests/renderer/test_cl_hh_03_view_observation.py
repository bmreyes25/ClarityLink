from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-renderer"))

from view_observation import (  # noqa: E402
    Bounds,
    EventKind,
    ImageScaleType,
    ObservationRecorder,
    ViewMetadata,
    ViewSnapshot,
    Visibility,
    WindowLabel,
    compare_snapshots,
)


def metadata(label: str, *, parent: tuple[str, ...] | None = (),
             attached: bool | None = True, bounds: Bounds | None = Bounds(0, 0, 100, 50),
             visible: Bounds | None = Bounds(0, 0, 100, 50),
             visibility: Visibility = Visibility.VISIBLE) -> ViewMetadata:
    return ViewMetadata(label, parent, attached, bounds, (0, 0), visible, visibility,
                        display_id=1, window_label=WindowLabel.WINDOW_0)


def snapshot(sequence: int, *, main: ViewMetadata | None = None,
             interrupt: ViewMetadata | None = None,
             injected: ViewMetadata | None = None,
             image: ViewMetadata | None = None) -> ViewSnapshot:
    return ViewSnapshot(sequence, sequence * 100, main, interrupt, injected, image,
                        source_frame_size=(400, 240), scale_type=ImageScaleType.FIT_XY,
                        image_matrix=(1.46, 0.0, 0.0, 0.0, 0.7958, 24.0, 0.0, 0.0, 1.0))


def test_known_and_unknown_runtime_geometry_are_preserved() -> None:
    known = metadata("root")
    unknown = metadata("root", parent=None, attached=None, bounds=None, visible=None,
                       visibility=Visibility.UNKNOWN)
    assert known.local_bounds == Bounds(0, 0, 100, 50)
    assert known.global_visible_rect == Bounds(0, 0, 100, 50)
    assert unknown.local_bounds is None
    assert unknown.global_visible_rect is None
    assert unknown.parent_chain is None
    assert unknown.attached is None


def test_attachment_detachment_and_parent_replacement_are_observable() -> None:
    before = snapshot(1, injected=metadata("injected", parent=("main", "window")))
    after = snapshot(2, injected=metadata("injected", parent=("interrupt", "window")))
    events = compare_snapshots(before, after)
    assert any(event.kind is EventKind.PARENT_CHAIN_CHANGED
               and event.target == "injected_view" for event in events)

    detached = snapshot(3, injected=metadata("injected", attached=False))
    assert any(event.kind is EventKind.DETACHED
               for event in compare_snapshots(after, detached))
    attached = snapshot(4, injected=metadata("injected", attached=True))
    assert any(event.kind is EventKind.ATTACHED
               for event in compare_snapshots(detached, attached))

    appeared = snapshot(5, injected=metadata("injected", attached=True))
    appearance_events = compare_snapshots(snapshot(4), appeared)
    assert any(event.kind is EventKind.NODE_APPEARED for event in appearance_events)
    assert not any(event.kind is EventKind.ATTACHED for event in appearance_events)


def test_interrupt_root_visibility_transition_is_not_labeled_warning_priority() -> None:
    before = snapshot(1, main=metadata("main"),
                      interrupt=metadata("interrupt", visibility=Visibility.GONE))
    after = snapshot(2, main=metadata("main", visibility=Visibility.INVISIBLE),
                     interrupt=metadata("interrupt", visibility=Visibility.VISIBLE))
    events = compare_snapshots(before, after)
    assert any(event.target == "interrupt_root"
               and event.kind is EventKind.VISIBILITY_CHANGED for event in events)
    assert all("warning" not in event.kind.value for event in events)


def test_global_visible_rect_and_display_window_metadata_are_recorded() -> None:
    view = metadata("image", visible=Bounds(10, 5, 80, 45))
    observed = snapshot(1, image=view)
    assert observed.image_view.global_visible_rect == Bounds(10, 5, 80, 45)
    assert observed.image_view.display_id == 1
    assert observed.image_view.window_label is WindowLabel.WINDOW_0


def test_local_geometry_display_and_image_configuration_changes_emit_events() -> None:
    before = snapshot(1, image=metadata("image"))
    changed_image = metadata("image", bounds=Bounds(0, 0, 80, 40),
                             visible=Bounds(0, 0, 100, 50))
    after = ViewSnapshot(2, 200, None, None, None, changed_image,
                         source_frame_size=(800, 480),
                         scale_type=ImageScaleType.CENTER_CROP,
                         image_matrix=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))
    events = compare_snapshots(before, after)
    kinds = {event.kind for event in events}
    assert EventKind.LOCAL_BOUNDS_CHANGED in kinds
    assert EventKind.SOURCE_FRAME_CHANGED in kinds
    assert EventKind.SCALE_TYPE_CHANGED in kinds
    assert EventKind.IMAGE_MATRIX_CHANGED in kinds


def test_capacity_is_bounded_and_fails_closed() -> None:
    recorder = ObservationRecorder(max_samples=2)
    assert recorder.record(snapshot(1))
    assert recorder.record(snapshot(2))
    assert recorder.capacity_reached
    assert not recorder.record(snapshot(3))
    assert len(recorder.samples) == 2
    assert len(recorder.events) <= 2 * 35


@pytest.mark.parametrize("limit", [0, -1, True, 4097])
def test_observer_initialization_failure_rejects_invalid_capacity(limit) -> None:
    with pytest.raises(ValueError):
        ObservationRecorder(limit)


def test_shutdown_is_safe_and_prevents_more_collection() -> None:
    recorder = ObservationRecorder(max_samples=4)
    first = snapshot(1)
    assert recorder.record(first)
    recorder.stop()
    assert recorder.closed
    assert not recorder.record(snapshot(2))
    assert recorder.samples == (first,)


def test_recorder_rejects_view_like_objects_without_mutating_them() -> None:
    class FakeView:
        mutation_count = 0

        def addView(self, *_args):
            self.mutation_count += 1

        def removeView(self, *_args):
            self.mutation_count += 1

    view = FakeView()
    recorder = ObservationRecorder()
    with pytest.raises(TypeError, match="ViewSnapshot"):
        recorder.record(view)  # type: ignore[arg-type]
    assert view.mutation_count == 0
    assert recorder.samples == ()


def test_recorder_rejects_snapshot_subclasses_that_could_retain_objects() -> None:
    class FakeView:
        pass

    @dataclass(frozen=True)
    class LeakySnapshot(ViewSnapshot):
        extra: object = None

    view = FakeView()
    sample = LeakySnapshot(1, 1, None, None, None, None, extra=view)
    recorder = ObservationRecorder()
    with pytest.raises(TypeError, match="ViewSnapshot"):
        recorder.record(sample)
    assert recorder.samples == ()


def test_snapshot_metadata_validation_rejects_malformed_values() -> None:
    with pytest.raises(ValueError):
        Bounds(1, 2, 1, 4)
    with pytest.raises(ValueError, match="two integer"):
        ViewMetadata("v", (), True, None, (1,), None)
    with pytest.raises(ValueError, match="source frame size"):
        ViewSnapshot(1, 1, None, None, None, None, source_frame_size=(1,))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite numeric"):
        ViewSnapshot(1, 1, None, None, None, None, image_matrix=(float("nan"),))
    with pytest.raises(ValueError, match="redacted"):
        ViewMetadata("image", (), True, None, None, None,
                     window_label="window-raw-token-value")  # type: ignore[arg-type]


def test_mutable_sequences_are_rejected_before_they_can_change_recorded_data() -> None:
    chain = ["parent"]
    location = [1, 2]
    matrix = [1.0] * 9
    with pytest.raises(ValueError, match="immutable tuple"):
        metadata("image", parent=chain)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="screen location"):
        ViewMetadata("image", (), True, None, location, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="image matrix"):
        ViewSnapshot(1, 1, None, None, None, None, image_matrix=matrix)  # type: ignore[arg-type]
    chain.append("later")
    location[0] = 999
    matrix[0] = 999.0


def test_snapshot_rejects_metadata_subclasses_and_unbounded_numbers() -> None:
    @dataclass(frozen=True)
    class LeakyMetadata(ViewMetadata):
        extra: object = None

    with pytest.raises(ValueError, match="immutable ViewMetadata"):
        ViewSnapshot(1, 1, LeakyMetadata("root", (), True, None, None, None, extra=object()),
                     None, None, None)
    with pytest.raises(ValueError, match="coordinate limit"):
        Bounds(0, 0, 10 ** 100, 1)
    with pytest.raises(ValueError, match="finite numeric"):
        ViewSnapshot(1, 1, None, None, None, None,
                     image_matrix=(10 ** 1000,) + (0,) * 8)
