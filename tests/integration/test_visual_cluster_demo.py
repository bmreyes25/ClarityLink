from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-sim"))

from export_visual_demo import build_visual_demo_payload


class VisualClusterDemoTests(unittest.TestCase):
    def test_screenstream_validation_status_requires_full_path_success(self):
        passed = {
            "status": "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM",
            "evidence": "SYNTHETIC_TEST_VALUE",
            "dimensions": [320, 180],
            "renderer_target": "Display 1 mock",
        }
        payload = build_visual_demo_payload(screenstream_validation=passed)
        state = payload["modes"]["hypothetical_type111"]
        self.assertEqual(payload["source"], "STEP_42E_REPLAY_OUTPUT+SYNTHETIC_SCREENSTREAM_H264_VALIDATION")
        self.assertEqual(state["cluster_frame"]["status_label"], "FRAME ARTIFACT UNAVAILABLE")
        self.assertTrue(state["cluster_frame"]["decoded_from_h264"])
        self.assertFalse(state["cluster_frame"]["actual_frame"]["available"])
        self.assertEqual(payload["live_test"], "NOT_READY")
        self.assertFalse(payload["modes"]["strict_honda"]["cluster_frame"]["visible"])

        failed = build_visual_demo_payload(screenstream_validation={
            "status": "ATTEMPTED_FAILED", "capabilities": {"ffmpeg_available": True},
        })
        self.assertEqual(failed["modes"]["hypothetical_type111"]["cluster_frame"]["status_label"],
                         "DECODE FAILED")

    def test_successful_synthetic_decode_is_labeled_without_advancing_live_gates(self):
        validation = {
            "status": "HOST_DECODED_SYNTHETIC_H264",
            "dimensions": [320, 180],
            "evidence": "SYNTHETIC_TEST_VALUE",
        }
        payload = build_visual_demo_payload(validation)
        hypothetical = payload["modes"]["hypothetical_type111"]
        self.assertEqual(hypothetical["cluster_frame"]["status_label"],
                         "HOST-DECODED SYNTHETIC H264")
        self.assertFalse(payload["modes"]["strict_honda"]["cluster_frame"]["visible"])
        self.assertEqual(payload["live_test"], "NOT_READY")
        self.assertEqual(payload["externaldisplay_live_render_test"], "NOT_READY")

    def test_data_is_projected_from_both_replay_modes(self):
        payload = build_visual_demo_payload()
        self.assertEqual(payload["source"], "STEP_42E_REPLAY_OUTPUT")
        strict = payload["modes"]["strict_honda"]
        hypothetical = payload["modes"]["hypothetical_type111"]
        self.assertTrue(strict["type110"]["active"] and strict["type110"]["unchanged"])
        self.assertFalse(strict["cluster_frame"]["visible"])
        self.assertEqual(strict["type111"]["status"], "skipped / unsupported")
        self.assertTrue(hypothetical["type110"]["active"] and hypothetical["type110"]["unchanged"])
        self.assertTrue(hypothetical["type111"]["listener_started"])
        self.assertTrue(hypothetical["type111"]["video_config_received"])
        self.assertTrue(hypothetical["type111"]["frame_received"])
        self.assertTrue(hypothetical["type111"]["renderer_submitted"])
        self.assertTrue(hypothetical["cluster_frame"]["visible"])
        self.assertFalse(hypothetical["cluster_frame"]["decoded_from_h264"])
        self.assertIn("SYNTHETIC FRAME SOURCE", hypothetical["cluster_frame"]["status_label"])
        self.assertIn(hypothetical["cluster_frame"]["decode_status"], {
            "HOST_DECODER_UNAVAILABLE", "NOT_RUN_SYNTHETIC_FIXTURE_NOT_VALID_H264",
        })
        self.assertTrue(hypothetical["audio"]["unchanged"])

    def test_evidence_and_unknowns_are_visible_in_both_modes(self):
        payload = build_visual_demo_payload()
        for state in payload["modes"].values():
            topics = {item["topic"] for item in state["unknowns"]}
            self.assertIn("Honda Type111 response schema", topics)
            self.assertIn("display-to-stream correlation", topics)
            self.assertIn("Type111 security and key derivation", topics)
            self.assertIn("real ExternalDisplay frame handoff", topics)
            self.assertIn("jmcs integration/load seam", topics)
        hypothetical = payload["modes"]["hypothetical_type111"]
        self.assertEqual(hypothetical["type111"]["evidence"], "MHI2_DERIVED_HYPOTHESIS")
        self.assertEqual(hypothetical["type111"]["field_values"], "SYNTHETIC_TEST_VALUE")
        self.assertEqual(hypothetical["renderer"]["crop_mask"], "UNKNOWN")
        labels = {item["label"] for item in hypothetical["evidence_labels"]}
        self.assertEqual(labels, {
            "HONDA_CONFIRMED", "MHI2_DERIVED_HYPOTHESIS", "SYNTHETIC_TEST_VALUE", "UNKNOWN"
        })

    def test_static_view_has_labels_controls_and_no_live_ready_claim(self):
        html = (ROOT / "demo/type111/index.html").read_text(encoding="utf-8")
        for text in (
            "HONDA_CONFIRMED", "MHI2_DERIVED_HYPOTHESIS", "SYNTHETIC_TEST_VALUE", "UNKNOWN",
            "Strict Honda", "Hypothetical Type111", "Unknown register", "replay-data.json",
            "NOT READY", "CROP / MASK UNKNOWN", "SYNTHETIC SCHEMATIC FALLBACK", "HOST DECODER UNAVAILABLE", "Evidence labels",
            "toggleAttribute('hidden'",
            "Candidate response fields", "MHI2 hypothesis",
            "ACTUAL DECODED SYNTHETIC FRAME", "screenstream_validation",
            "Not Honda output · Not CarPlay content · Offline test fixture",
            "FRAME ARTIFACT UNAVAILABLE — SCHEMATIC FALLBACK",
        ):
            self.assertIn(text, html)
        self.assertNotIn("PRESENTED_AS_LIVE_READY", html)
        self.assertNotIn("sessionKey", html)
        self.assertNotIn("assets/center-", html)

    def test_generated_payload_is_json_serializable_and_keeps_live_gates_closed(self):
        payload = build_visual_demo_payload()
        encoded = json.dumps(payload)
        self.assertIn('"live_test": "NOT_READY"', encoded)
        self.assertIn('"jmcs_noop_test": "NOT_READY"', encoded)
        self.assertIn('"externaldisplay_live_render_test": "NOT_READY"', encoded)
        self.assertEqual(payload["ld_preload"], "PARKED")

    def test_committed_data_asset_matches_canonical_replay_export(self):
        data_path = ROOT / "demo/type111/replay-data.json"
        stored = json.loads(data_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema"], "claritylink.synthetic-type111-visual-demo.v1")
        self.assertEqual(stored["live_test"], "NOT_READY")
        self.assertEqual(stored["jmcs_noop_test"], "NOT_READY")
        self.assertEqual(stored["externaldisplay_live_render_test"], "NOT_READY")
        validation = stored["host_decode_validation"]
        visual_frame = stored["modes"]["hypothetical_type111"]["cluster_frame"].get("actual_frame")
        rebuilt = build_visual_demo_payload(validation, stored.get("screenstream_validation"), visual_frame)
        self.assertEqual(rebuilt["modes"]["strict_honda"]["type110"],
                         stored["modes"]["strict_honda"]["type110"])
        self.assertEqual(rebuilt["modes"]["hypothetical_type111"]["type110"],
                         stored["modes"]["hypothetical_type111"]["type110"])
        self.assertEqual(rebuilt["modes"]["hypothetical_type111"]["cluster_frame"]["status_label"],
                         stored["modes"]["hypothetical_type111"]["cluster_frame"]["status_label"])


if __name__ == "__main__":
    unittest.main()
