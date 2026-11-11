"""Pixel-level tests for the offline in-memory Display 1 host equivalent."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))
from host_raster_backend import (  # noqa: E402
    HostBoundaryError, RasterDisplay1HostBackend, StaleHostLease, ViewBounds,
)
from model import DecodedFrame, DisplayTarget, PIXEL_FORMAT  # noqa: E402


def rgba_frame(width=2, height=2, *, pixels=None, timestamp=1, pixel_format=PIXEL_FORMAT,
              crop=None, rotation=0):
    pixels = pixels if pixels is not None else bytes((
        255, 0, 0, 255, 0, 255, 0, 255,
        0, 0, 255, 255, 255, 255, 255, 255,
    ))
    return DecodedFrame(width, height, pixel_format, width * 4, timestamp,
                        rgba=pixels, crop=crop, rotation_degrees=rotation)


def test_frame_pixels_are_scaled_into_host_view_and_clipped_to_surface():
    backend = RasterDisplay1HostBackend(ViewBounds(790, 470, 30, 30))
    lease = backend.attach(DisplayTarget())
    backend.submit(rgba_frame(), lease)
    surface = backend.surface
    assert surface is not None
    assert surface.pixel(799, 479) == (255, 0, 0, 255)
    assert surface.pixel(789, 479) == (0, 0, 0, 0)
    assert len(surface.snapshot()) == 800 * 480 * 4


def test_crop_rotation_and_scaling_are_applied_before_view_clipping():
    backend = RasterDisplay1HostBackend(ViewBounds(0, 0, 2, 2))
    lease = backend.attach(DisplayTarget())
    backend.submit(rgba_frame(crop=(0, 0, 2, 2), rotation=90), lease)
    surface = backend.surface
    assert surface is not None
    # 90 degrees clockwise: top-left becomes the source's lower-left (blue).
    assert surface.pixel(0, 0) == (0, 0, 255, 255)
    assert surface.pixel(1, 0) == (255, 0, 0, 255)
    assert surface.pixel(0, 1) == (255, 255, 255, 255)
    assert surface.pixel(1, 1) == (0, 255, 0, 255)


@pytest.mark.parametrize("bad_frame", [
    DecodedFrame(0, 2, PIXEL_FORMAT, 0, 1, rgba=b""),
    DecodedFrame(1, 1, "RGB24", 4, 1, rgba=bytes(4)),
    DecodedFrame(2, 2, PIXEL_FORMAT, 4, 1, rgba=bytes(16)),
])
def test_invalid_dimensions_format_and_stride_are_rejected(bad_frame):
    backend = RasterDisplay1HostBackend(ViewBounds(0, 0, 2, 2))
    lease = backend.attach(DisplayTarget())
    with pytest.raises(ValueError):
        backend.submit(bad_frame, lease)
    assert backend.accepted_frames == 0


def test_navigation_deselect_revokes_view_surface_and_old_lease():
    backend = RasterDisplay1HostBackend(ViewBounds(0, 0, 2, 2))
    old_lease = backend.attach(DisplayTarget())
    backend.submit(rgba_frame(), old_lease)
    old_surface = backend.surface
    backend.set_navigation_selected(False)
    assert backend.surface is None and backend.attached is False
    assert old_surface is not None and old_surface.destroyed is True
    assert backend.destroyed_surfaces == 1
    backend.set_navigation_selected(True)
    assert backend.surface is None  # selection never restores stale content
    with pytest.raises(StaleHostLease):
        backend.submit(rgba_frame(timestamp=2), old_lease)
    new_lease = backend.attach(DisplayTarget())
    assert new_lease.generation > old_lease.generation
    assert backend.surface is not old_surface


def test_session_end_and_host_loss_destroy_surfaces_and_require_fresh_lease():
    backend = RasterDisplay1HostBackend(ViewBounds(0, 0, 2, 2))
    first = backend.attach(DisplayTarget())
    backend.submit(rgba_frame(), first)
    old_surface = backend.surface
    backend.terminate_parent_session()
    assert old_surface is not None and old_surface.destroyed
    assert backend.surface is None
    with pytest.raises(HostBoundaryError):
        backend.attach(DisplayTarget())

    backend.begin_parent_session()
    restored = backend.attach(DisplayTarget())
    restored_surface = backend.surface
    backend.submit(rgba_frame(timestamp=2), restored)
    backend.host_lost()
    assert restored_surface is not None and restored_surface.destroyed
    assert backend.surface is None
    with pytest.raises(StaleHostLease):
        backend.submit(rgba_frame(timestamp=3), restored)
    backend.host_restored()
    assert backend.surface is None  # host return does not reinsert a View
    fresh = backend.attach(DisplayTarget())
    backend.submit(rgba_frame(timestamp=4), fresh)
    assert backend.accepted_frames == 3


def test_clear_removes_stale_pixels_without_destroying_view_until_close():
    backend = RasterDisplay1HostBackend(ViewBounds(0, 0, 2, 2))
    lease = backend.attach(DisplayTarget())
    backend.submit(rgba_frame(), lease)
    surface = backend.surface
    assert surface is not None and surface.pixel(0, 0) != (0, 0, 0, 0)
    backend.clear(lease)
    assert backend.surface is surface and surface.pixel(0, 0) == (0, 0, 0, 0)
    backend.close(lease)
    assert backend.surface is None and surface.destroyed
    assert backend.created_surfaces == backend.destroyed_surfaces == 1


@pytest.mark.parametrize("bounds", [
    ViewBounds(0, 0, 0, 10),
    ViewBounds(0, 0, 800 * 4 + 1, 10),
    ViewBounds(800 * 4 + 1, 0, 1, 1),
])
def test_unbounded_or_empty_view_geometry_is_rejected(bounds):
    with pytest.raises(HostBoundaryError):
        RasterDisplay1HostBackend(bounds)
