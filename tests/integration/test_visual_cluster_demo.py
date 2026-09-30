from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-sim"))

from export_visual_demo import build_visual_demo_payload


class VisualClusterDemoTests(unittest.TestCase):
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
            "NOT READY", "CROP / MASK UNKNOWN", "not decoded H.264", "Evidence labels",
            "toggleAttribute('hidden'",
            "Candidate response fields", "MHI2 hypothesis",
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
        self.assertEqual(json.loads(data_path.read_text(encoding="utf-8")), build_visual_demo_payload())


if __name__ == "__main__":
    unittest.main()
