import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model import (
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    PIXEL_FORMAT,
    ClarityLinkRenderer,
    DecodedFrame,
    DisplayTarget,
    MockDisplay1Backend,
    SyntheticPatternSource,
)


class RendererTests(unittest.TestCase):
    def test_target_is_display1_800x480(self):
        target = DisplayTarget()
        target.validate()
        self.assertEqual((target.display_id, target.width, target.height), (1, 800, 480))

    def test_pattern_frame_size_and_stride(self):
        frame = SyntheticPatternSource().next_frame(
            datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)
        )
        frame.validate(require_cpu=True)
        self.assertEqual((frame.width, frame.height), (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        self.assertEqual(frame.row_stride, DISPLAY_WIDTH * 4)
        self.assertEqual(len(frame.rgba), DISPLAY_WIDTH * DISPLAY_HEIGHT * 4)
        self.assertEqual(frame.pixel_format, PIXEL_FORMAT)

    def test_invalid_target_size_rejected(self):
        with self.assertRaises(ValueError):
            DisplayTarget(width=799).validate()

    def test_invalid_frame_dimensions_and_stride_rejected(self):
        bad_size = DecodedFrame(0, 480, PIXEL_FORMAT, 3200, 0, rgba=b"")
        bad_stride = DecodedFrame(800, 480, PIXEL_FORMAT, 3199, 0, rgba=b"x" * 3199 * 480)
        with self.assertRaises(ValueError):
            bad_size.validate()
        with self.assertRaises(ValueError):
            bad_stride.validate()

    def test_surface_backed_frame_is_contract_only(self):
        frame = DecodedFrame(800, 480, PIXEL_FORMAT, 3200, 123, surface_token="decoder-surface")
        frame.validate()
        with self.assertRaises(ValueError):
            frame.validate(require_cpu=True)

    def test_backend_lifecycle_clear_and_destroy(self):
        backend = MockDisplay1Backend()
        renderer = ClarityLinkRenderer(backend)
        renderer.start()
        self.assertEqual(backend.events, ["attach"])
        renderer.close()
        self.assertEqual(backend.events, ["attach", "clear", "close"])
        self.assertIsNone(backend.target)

    def test_repeated_frame_submission(self):
        backend = MockDisplay1Backend()
        renderer = ClarityLinkRenderer(backend)
        source = SyntheticPatternSource()
        renderer.start()
        renderer.submit(source.next_frame())
        renderer.submit(source.next_frame())
        self.assertEqual(len(backend.frames), 2)
        self.assertNotEqual(backend.frames[0].rgba, backend.frames[1].rgba)
        renderer.close()
        self.assertEqual(backend.frames, [])

    def test_submission_requires_started_renderer(self):
        with self.assertRaises(RuntimeError):
            ClarityLinkRenderer(MockDisplay1Backend()).submit(
                SyntheticPatternSource().next_frame()
            )


if __name__ == "__main__":
    unittest.main()
