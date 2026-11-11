"""Generated Type111 -> decoder -> pixel Surface prototype, on a host-only canvas.

All H.264 and lab framing are generated locally. This is no iPhone, Android
SurfaceFlinger, Honda receiver, or vehicle compatibility test.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

import t111_synth as synth  # noqa: E402
from host_raster_backend import (  # noqa: E402
    RasterDisplay1HostBackend, StaleHostLease, ViewBounds,
    synthetic_type111_rgb24_to_rgba,
)
from model import DisplayTarget  # noqa: E402
from claritylink_jmcs.display import NullDisplay  # noqa: E402
from type111_ingest import Type111IngestPipeline  # noqa: E402


def test_generated_type111_pixels_render_and_withdraw_without_affecting_type110():
    stream = synth.SyntheticStream(2)
    primary_display = NullDisplay()
    pipeline = Type111IngestPipeline(
        lab_mode=True, clock=synth.Clock(), primary_display=primary_display,
        receiver_kwargs=dict(synth.DIMENSIONS),
    )
    canvas = RasterDisplay1HostBackend(ViewBounds(0, 0, 584, 191))
    client = primary = None
    try:
        client, primary = synth.start_type111(pipeline, with_primary=True)

        # Preserve an active Type110 frame while processing secondary Type111.
        primary.sendall(stream.primary_message(0))
        assert pipeline.receiver.receive_primary_frame(pipeline.generation).startswith(b"\x89PNG")
        held_type110 = primary_display.current
        assert held_type110 is not None

        client.sendall(stream.config_message())
        assert pipeline.pump_frame().accepted  # VideoConfig, no pixels yet
        client.sendall(stream.frame_message(0))
        outcome = pipeline.pump_frame()
        assert outcome.accepted and outcome.frame is not None
        lab_frame = outcome.frame.frame
        assert lab_frame.stream_type == 111
        synth.assert_pixels_match(lab_frame, 0)

        rgba = synthetic_type111_rgb24_to_rgba(lab_frame)
        lease = canvas.attach(DisplayTarget())
        canvas.submit(rgba, lease)
        surface = canvas.surface
        assert surface is not None
        left, right = synth.expected_colors(0)
        for actual, expected in ((surface.pixel(146, 95), left),
                                 (surface.pixel(438, 95), right)):
            assert all(abs(a - b) <= synth.COLOR_TOLERANCE
                       for a, b in zip(actual[:3], expected))
            assert actual[3] == 255

        # Navigation deselection destroys the whole synthetic Surface and fences
        # a late Type111 frame; it does not touch the independent Type110 output.
        canvas.set_navigation_selected(False)
        assert surface.destroyed and canvas.surface is None
        try:
            canvas.submit(rgba, lease)
        except StaleHostLease:
            pass
        else:
            raise AssertionError("stale Type111 host lease was accepted")
        assert primary_display.current is held_type110
        assert pipeline.receiver.primary_decoder is not None
        assert not pipeline.receiver.primary_decoder.closed

        report = pipeline.end_type111()
        assert not report.failed
        assert pipeline.host.visible_content is None
        canvas.close(lease)  # host adapter receives the stream-end boundary event
        assert surface.destroyed and canvas.surface is None
        assert primary_display.current is held_type110
    finally:
        canvas.close()
        if client is not None:
            client.close()
        if primary is not None:
            primary.close()
        pipeline.receiver.teardown(pipeline.generation)
