import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "carplay-session-model" / "model.py"
SPEC = importlib.util.spec_from_file_location("claritylink_carplay_model", MODULE_PATH)
model = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)


class SessionModelTests(unittest.TestCase):
    def test_honda_primary_baseline_uses_configured_values(self):
        primary = model.honda_primary_model()
        self.assertEqual((primary.primary.width, primary.primary.height), (800, 480))
        self.assertEqual(primary.primary.max_fps, 30)
        self.assertEqual(primary.primary.touch_mode, "hifi")
        self.assertIsNone(primary.primary.display_uuid)
        self.assertIsNone(primary.secondary)

    def test_candidate_display_b_preserves_primary_and_uses_output_canvas(self):
        candidate = model.candidate_cluster_model()
        self.assertEqual(candidate.primary, model.honda_primary_model().primary)
        self.assertEqual((candidate.secondary.width, candidate.secondary.height), (800, 480))
        self.assertEqual(candidate.secondary.role, model.DisplayRole.CLUSTER_CANDIDATE)

    def test_unique_explicit_display_uuids_are_required(self):
        primary = model.DisplayDescriptor(model.DisplayRole.CENTER_MAIN, 800, 480, "00000000-0000-0000-0000-000000000001")
        secondary = model.DisplayDescriptor(model.DisplayRole.CLUSTER_CANDIDATE, 800, 480, "00000000-0000-0000-0000-000000000001")
        with self.assertRaisesRegex(ValueError, "must be unique"):
            model.CarPlaySessionModel(primary, secondary)

    def test_invalid_dimensions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "dimensions must be positive"):
            model.DisplayDescriptor(model.DisplayRole.CLUSTER_CANDIDATE, 0, 480)

    def test_session_identity_must_bind_to_secondary_display(self):
        secondary = model.DisplayDescriptor(model.DisplayRole.CLUSTER_CANDIDATE, 800, 480, "00000000-0000-0000-0000-000000000002")
        session = model.VideoSessionDescriptor("00000000-0000-0000-0000-000000000003")
        with self.assertRaisesRegex(ValueError, "must reference"):
            model.CarPlaySessionModel(model.honda_primary_model().primary, secondary, session)

    def test_deterministic_fixture_and_unknowns_are_explicit(self):
        candidate = model.candidate_cluster_model()
        self.assertEqual(candidate.deterministic_json(), candidate.deterministic_json())
        rendered = candidate.deterministic_json().decode("utf-8")
        self.assertIn('"wire_protocol_encoding":"unknown-not-emitted"', rendered)
        self.assertIn('"status":"unknown"', rendered)

    def test_secondary_session_teardown_is_independent_in_model(self):
        primary = model.honda_primary_model().primary
        before = model.CarPlaySessionModel(primary)
        candidate = model.candidate_cluster_model()
        after_teardown = model.CarPlaySessionModel(candidate.primary)
        self.assertEqual(before.primary, after_teardown.primary)
        self.assertIsNone(after_teardown.secondary_session)


if __name__ == "__main__":
    unittest.main()
