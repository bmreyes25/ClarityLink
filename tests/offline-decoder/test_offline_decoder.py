import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(__file__).with_name("run_dual_decode.py")
SPEC = importlib.util.spec_from_file_location("run_dual_decode", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OfflineDualDecodeTests(unittest.TestCase):
    def test_two_independent_decoders_replay_entire_fixture(self):
        if not MODULE.DEFAULT_FFMPEG.is_file() or not MODULE.DEFAULT_FIXTURE.is_file():
            self.skipTest(
                "optional local decoder-capacity artifacts are absent; "
                "the portable synthetic H.264 test runs separately"
            )
        self.assertTrue(MODULE.DEFAULT_FFMPEG.is_file(), "local bundled FFmpeg is required")
        self.assertTrue(MODULE.DEFAULT_FIXTURE.is_file(), "local 800x480 H.264 fixture is required")
        result = MODULE.decode_twice(MODULE.DEFAULT_FFMPEG, MODULE.DEFAULT_FIXTURE)
        self.assertTrue(result["passed"], result)
        self.assertEqual([stream["reportedFrames"] for stream in result["streams"]], [30, 30])
        self.assertEqual(len({stream["decoder"] for stream in result["streams"]}), 2)
        self.assertRegex(result["fixtureSha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
