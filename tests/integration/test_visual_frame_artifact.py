from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import sys
import tempfile
import unittest
from unittest import mock
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-sim"))
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

import export_visual_demo  # noqa: E402
from export_visual_demo import (  # noqa: E402
    build_visual_demo_payload, clear_visual_frame_artifacts, main, write_visual_frame,
)
from model import DecodedFrame, PIXEL_FORMAT  # noqa: E402


def decode_rgba_png(png: bytes) -> tuple[int, int, bytes]:
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8
    chunks = {}
    while offset < len(png):
        size = struct.unpack(">I", png[offset:offset + 4])[0]
        kind = png[offset + 4:offset + 8]
        payload = png[offset + 8:offset + 8 + size]
        chunks.setdefault(kind, []).append(payload)
        offset += size + 12
        if kind == b"IEND":
            break
    width, height, depth, color_type, *_ = struct.unpack(">IIBBBBB", chunks[b"IHDR"][0])
    assert (depth, color_type) == (8, 6)
    scanlines = zlib.decompress(b"".join(chunks[b"IDAT"]))
    row_bytes = width * 4
    rows = [scanlines[row * (row_bytes + 1):(row + 1) * (row_bytes + 1)] for row in range(height)]
    assert all(row[0] == 0 for row in rows)
    return width, height, b"".join(row[1:] for row in rows)


class VisualFrameArtifactTests(unittest.TestCase):
    def test_png_pixels_and_provenance_match_exact_rgba_frame(self):
        rgba = bytes((255, 0, 32, 255, 0, 210, 80, 255))
        frame = DecodedFrame(2, 1, PIXEL_FORMAT, 8, 123, rgba=rgba)
        with tempfile.TemporaryDirectory() as scratch:
            runtime = Path(scratch)
            metadata = write_visual_frame(frame, runtime)
            width, height, recovered = decode_rgba_png((runtime / "type111-frame.png").read_bytes())
            self.assertEqual((width, height), (2, 1))
            self.assertEqual(recovered, rgba)
            self.assertEqual(metadata["sha256"], hashlib.sha256(recovered).hexdigest())
            self.assertEqual(metadata["rgbaBytes"], 8)
            self.assertEqual(metadata["evidence"], "SYNTHETIC_TEST_VALUE")

    def test_wrong_rgba_length_is_rejected(self):
        frame = DecodedFrame(2, 1, PIXEL_FORMAT, 8, 0, rgba=b"short")
        with tempfile.TemporaryDirectory() as scratch:
            with self.assertRaises(ValueError):
                write_visual_frame(frame, Path(scratch))

    def test_artifact_write_failure_is_not_reported_as_available(self):
        frame = DecodedFrame(1, 1, PIXEL_FORMAT, 4, 0, rgba=b"\x01\x02\x03\xff")
        with tempfile.TemporaryDirectory() as scratch:
            blocked = Path(scratch) / "not-a-directory"
            blocked.write_text("block directory creation", encoding="utf-8")
            with self.assertRaises(OSError):
                write_visual_frame(frame, blocked)
            self.assertFalse((Path(scratch) / "type111-frame.png").exists())

    def test_prior_success_artifact_is_removed_before_new_attempt(self):
        with tempfile.TemporaryDirectory() as scratch:
            runtime = Path(scratch)
            runtime.mkdir(exist_ok=True)
            (runtime / "type111-frame.png").write_bytes(b"old success")
            (runtime / "frame-metadata.json").write_text('{"available":true}')
            (runtime / ".type111-frame.png.tmp").write_bytes(b"interrupted write")
            clear_visual_frame_artifacts(runtime)
            self.assertFalse((runtime / "type111-frame.png").exists())
            self.assertFalse((runtime / "frame-metadata.json").exists())
            self.assertFalse((runtime / ".type111-frame.png.tmp").exists())

    def test_new_failed_generation_removes_old_frame_and_records_fallback(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            runtime = root / "demo/type111/runtime"
            runtime.mkdir(parents=True)
            frame_path = runtime / "type111-frame.png"
            frame_path.write_bytes(b"old successful PNG")
            (runtime / "frame-metadata.json").write_text('{"available":true}')
            def fail_after_cleanup():
                self.assertFalse(frame_path.exists(), "stale frame must be removed before generation starts")
                return {"status": "ATTEMPTED_FAILED", "reason": "synthetic decode failure",
                        "capabilities": {"ffmpeg_available": True}, "evidence": "SYNTHETIC_TEST_VALUE"}
            with mock.patch.object(export_visual_demo, "ROOT", root), \
                    mock.patch.object(export_visual_demo, "run_screenstream_h264_validation", fail_after_cleanup), \
                    mock.patch.object(sys, "argv", ["export_visual_demo.py", "--screenstream-h264"]):
                self.assertEqual(main(), 1)
            self.assertFalse(frame_path.exists())
            data = json.loads((root / "demo/type111/replay-data.json").read_text())
            cluster = data["modes"]["hypothetical_type111"]["cluster_frame"]
            self.assertEqual(cluster["status_label"], "DECODE FAILED")
            self.assertFalse(cluster["actual_frame"]["available"])

    def test_demo_only_claims_actual_frame_with_available_artifact_and_strict_stays_empty(self):
        validation = {"status": "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM"}
        metadata = {
            "available": True, "asset": "runtime/type111-frame.png", "width": 320,
            "height": 180, "pixelFormat": "RGBA8888", "rgbaBytes": 230400,
            "sha256": "abc123", "evidence": "SYNTHETIC_TEST_VALUE",
        }
        payload = build_visual_demo_payload(screenstream_validation=validation,
                                            visual_frame_metadata=metadata)
        strict = payload["modes"]["strict_honda"]["cluster_frame"]
        hypothetical = payload["modes"]["hypothetical_type111"]["cluster_frame"]
        self.assertFalse(strict["actual_frame"]["available"])
        self.assertTrue(hypothetical["actual_frame"]["available"])
        self.assertEqual(hypothetical["status_label"], "ACTUAL DECODED SYNTHETIC FRAME VIA SCREENSTREAM")
        self.assertEqual((hypothetical["actual_frame"]["width"], hypothetical["actual_frame"]["height"]), (320, 180))

    def test_success_without_visual_artifact_is_not_claimed_as_visible(self):
        payload = build_visual_demo_payload(
            screenstream_validation={"status": "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM"}
        )
        hypothetical = payload["modes"]["hypothetical_type111"]["cluster_frame"]
        self.assertEqual(hypothetical["status_label"], "FRAME ARTIFACT UNAVAILABLE")
        self.assertFalse(hypothetical["actual_frame"]["available"])

    def test_runtime_media_path_is_gitignored_and_ui_has_explicit_fallback(self):
        import subprocess
        result = subprocess.run(
            ["git", "check-ignore", "demo/type111/runtime/type111-frame.png"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (ROOT / "demo/type111/index.html").read_text(encoding="utf-8")
        self.assertIn("ACTUAL DECODED SYNTHETIC FRAME", html)
        self.assertIn("Not Honda output · Not CarPlay content · Offline test fixture", html)
        self.assertIn("FRAME ARTIFACT UNAVAILABLE — SCHEMATIC FALLBACK", html)
        self.assertIn("object-fit:contain", html)


if __name__ == "__main__":
    unittest.main()
