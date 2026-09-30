import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-sim"))

from capability_gating import CapabilityInputs, ReplayMode, evaluate_capability_gate
from synthetic_type111_replay import synthetic_type111_cluster_replay


class SyntheticType111ReplayTests(unittest.TestCase):
    def test_strict_honda_mode_skips_candidate_and_preserves_stock_type110(self):
        result = synthetic_type111_cluster_replay(ReplayMode.STRICT_HONDA)
        self.assertFalse(result["decision"].allowed)
        self.assertEqual(result["stock_calls"], ["stock"])
        self.assertEqual(result["stock_response"], result["stock_baseline"])
        self.assertEqual(result["hypothetical_type111_response"], [])
        self.assertEqual(result["renderer_frame_count"], 0)
        self.assertEqual(result["server_info"], result["original_server_info"])
        self.assertTrue(result["type110_snapshot"]["center_display"] == "stock-type110-active")
        self.assertFalse(result["full_session_state"]["type110_active"])
        self.assertIn("full_session_teardown", [item["event"] for item in result["events"]])
        self.assertIn("Honda Type111 response schema", result["unknown_honda_fields"])

    def test_hypothetical_mode_runs_full_synthetic_stream_and_mock_render(self):
        result = synthetic_type111_cluster_replay(ReplayMode.HYPOTHETICAL_TYPE111)
        self.assertTrue(result["decision"].allowed)
        self.assertEqual(result["stock_calls"], ["stock"])
        self.assertEqual(result["stock_response"]["streams"][:2],
                         result["stock_baseline"]["streams"])
        self.assertEqual(result["stock_response"]["streams"][1]["dataPort"], 42110)
        self.assertEqual(result["setup_request"]["streams"][1]["streamConnectionID"], 42001)
        self.assertEqual(result["setup_request"], result["setup_request_baseline"])
        self.assertNotIn("streamConnectionID", result["stock_response"]["streams"][1])
        self.assertEqual(result["hypothetical_type111_response"][0]["type"], 111)
        self.assertEqual(result["hypothetical_type111_response"][0]["streamID"], 111)
        self.assertEqual(len(result["server_info"]["displays"]), 2)
        self.assertEqual(result["field_provenance"]["Type111 response profile"],
                         "MHI2_DERIVED_HYPOTHESIS")
        self.assertEqual(result["renderer_frame_count"], 1)
        self.assertEqual(result["video_handoff_mode"], "SYNTHETIC_FRAME_SOURCE")
        self.assertEqual(result["renderer_events"], ["attach", "submit", "clear", "close"])
        self.assertTrue(result["synthetic_secrets_cleared"])
        self.assertEqual((result["decoded_frame"].width, result["decoded_frame"].height), (800, 480))
        self.assertGreater(result["decoded_frame"].presentation_time_ns, 0)
        self.assertEqual(result["renderer_received_frame"], result["decoded_frame"])
        self.assertEqual(result["type110_snapshot"]["center_display"], "stock-type110-active")
        self.assertEqual(result["audio_snapshot"]["center_active"], True)
        self.assertTrue(result["after_type111_teardown"]["type110_active"])
        events = [item["event"] for item in result["events"]]
        self.assertLess(events.index("type110_setup_preserved"), events.index("capability_gate_checked"))
        self.assertLess(events.index("type111_videoconfig_received"), events.index("type111_frame_received"))
        self.assertLess(events.index("type111_frame_received"), events.index("type111_frame_submitted_to_renderer"))
        self.assertLess(events.index("type111_teardown"), events.index("type110_still_active"))
        self.assertIn("audio_state_unchanged", events)
        self.assertEqual(result["after_type111_teardown"]["audio"], result["audio_snapshot"])
        self.assertEqual(result["after_type111_teardown"]["renderer_attached"], False)
        self.assertEqual(result["safety_overlay"], "UNKNOWN_NOT_RENDERED_BY_MOCK")
        self.assertEqual(result["crop_mask"], "UNKNOWN")
        self.assertEqual(result["full_session_state"]["type110_active"], False)
        self.assertEqual(result["full_session_state"]["audio"]["center_active"], False)
        self.assertTrue(result["annex_b_access_unit"].startswith(b"\x00\x00\x00\x01\x67\x42"))
        self.assertTrue(result["display_pts_is_synthetic"])
        self.assertEqual(result["video_handoff_mode"], "SYNTHETIC_FRAME_SOURCE")
        self.assertEqual([entry["event"] for entry in result["events"][:5]],
                         ["session_started", "type110_setup_started", "type110_setup_preserved",
                          "capability_gate_checked", "type111_allowed_hypothetical"])
        self.assertTrue(any(entry["event"] == "type111_frame_submitted_to_renderer"
                            for entry in result["events"]))
        self.assertEqual(result["renderer_target"], None, "closed mock should release Display 1")

    def test_switching_modes_does_not_mutate_type110_snapshot(self):
        strict = synthetic_type111_cluster_replay(ReplayMode.STRICT_HONDA)
        hypothetical = synthetic_type111_cluster_replay(ReplayMode.HYPOTHETICAL_TYPE111)
        self.assertEqual(strict["type110_snapshot"], hypothetical["type110_snapshot"])
        self.assertEqual(strict["audio_snapshot"], hypothetical["audio_snapshot"])

    def test_host_decode_status_keeps_parser_fixture_and_fallback_distinct(self):
        result = synthetic_type111_cluster_replay(ReplayMode.HYPOTHETICAL_TYPE111)
        self.assertFalse(result["host_decode"]["performed"])
        self.assertEqual(result["video_handoff_mode"], "SYNTHETIC_FRAME_SOURCE")
        self.assertIn("synthetic_frame_source_fallback", [e["event"] for e in result["events"]])
        self.assertEqual(result["stock_response"]["streams"][:2],
                         result["stock_baseline"]["streams"])
        self.assertTrue(result["after_type111_teardown"]["type110_active"])
        self.assertEqual(result["after_type111_teardown"]["audio"], result["audio_snapshot"])

    def test_hypothetical_gate_requires_every_prerequisite_and_explicit_unknowns(self):
        inputs = CapabilityInputs(True, True, True, True, True, True, True, True)
        allowed = evaluate_capability_gate(ReplayMode.HYPOTHETICAL_TYPE111, inputs)
        self.assertTrue(allowed.allowed)
        for field in (
            "session_active", "type110_established", "capability_advertised",
            "display_descriptor_available", "stream_fields_available",
            "synthetic_security_inputs_available", "renderer_target_available",
            "unknown_honda_fields_explicit",
        ):
            values = dict(
                session_active=True, type110_established=True, capability_advertised=True,
                display_descriptor_available=True, stream_fields_available=True,
                synthetic_security_inputs_available=True, renderer_target_available=True,
                unknown_honda_fields_explicit=True,
            )
            values[field] = False
            decision = evaluate_capability_gate(ReplayMode.HYPOTHETICAL_TYPE111,
                                                CapabilityInputs(**values))
            self.assertFalse(decision.allowed, field)
            self.assertIn(field, decision.blockers)
        strict = evaluate_capability_gate(ReplayMode.STRICT_HONDA, inputs)
        self.assertFalse(strict.allowed)
        self.assertIn("not confirmed", strict.blockers[0])

    def test_unknown_fields_and_evidence_classes_are_visible(self):
        result = synthetic_type111_cluster_replay(ReplayMode.HYPOTHETICAL_TYPE111)
        self.assertIn("display/stream correlation", result["unknown_honda_fields"])
        self.assertIn("MHI2_DERIVED_HYPOTHESIS", result["evidence"])
        response = result["hypothetical_type111_response"][0]
        self.assertNotIn("key", response)
        self.assertNotIn("iv", response)
        self.assertEqual(result["field_provenance"]["Type111 response profile"],
                         "MHI2_DERIVED_HYPOTHESIS")


if __name__ == "__main__":
    unittest.main()
