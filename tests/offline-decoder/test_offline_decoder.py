import base64
import importlib.util
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(__file__).with_name("run_dual_decode.py")
SPEC = importlib.util.spec_from_file_location("run_dual_decode", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OfflineDualDecodeTests(unittest.TestCase):
    def test_cl_imp_08_dual_stream_and_resolution_fixtures_are_decodable(self):
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            self.skipTest("FFmpeg is required to validate the H.264 fixture")
        fixtures = (("type110-red-32x32.h264.b64", (32, 32)),
                    ("type111-blue-32x32.h264.b64", (32, 32)),
                    ("type111-green-64x64.h264.b64", (64, 64)))
        for name, dimensions in fixtures:
            with self.subTest(fixture=name):
                fixture = ROOT / "tests/fixtures/cl-imp-08" / name
                access_unit = base64.b64decode(fixture.read_bytes().strip(), validate=True)
                result = subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "h264", "-i", "pipe:0",
                     "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
                    input=access_unit, capture_output=True, timeout=5, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                self.assertTrue(result.stdout.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual((int.from_bytes(result.stdout[16:20], "big"),
                                  int.from_bytes(result.stdout[20:24], "big")), dimensions)

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
