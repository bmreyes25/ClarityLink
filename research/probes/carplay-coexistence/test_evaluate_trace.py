import importlib.util
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("evaluate_trace", Path(__file__).with_name("evaluate_trace.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def trace(produced=30, gap_ns=66_666_667, eos=True, planned=30, input_gap_ns=66_666_667):
    events = [{"event": "start", "planned_frames": planned, "width": 800, "height": 480, "fps": 15},
              {"event": "format", "width": 800, "height": 480}]
    events += [{"event": "input", "pts_us": i * 66_667, "mono_ns": i * input_gap_ns} for i in range(planned)]
    events += [{"event": "output", "pts_us": i * 66_667, "mono_ns": (i + 1) * gap_ns} for i in range(produced)]
    if eos:
        events.append({"event": "eos"})
    return events


class TraceTests(unittest.TestCase):
    def test_old_28_of_30_result_is_below_95_percent(self):
        result = MODULE.evaluate(trace(28))
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertEqual(result["required_output"], 29)
        self.assertEqual(result["output_percent"], 93.33)

    def test_29_of_30_with_drain_and_cadence_passes_decoder_only(self):
        result = MODULE.evaluate(trace(29))
        self.assertEqual(result["decoder_gate"], "PASS")
        self.assertIn("UNOBSERVED", result["carplay_picture_voice_verdict"])

    def test_855_of_900_is_exact_60_second_threshold(self):
        result = MODULE.evaluate(trace(855, planned=900))
        self.assertEqual(result["required_output"], 855)
        self.assertEqual(result["decoder_gate"], "PASS")

    def test_fast_submitted_run_does_not_count_as_60_seconds(self):
        result = MODULE.evaluate(trace(900, planned=900, input_gap_ns=1_000_000))
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertIn("input run shorter than planned duration", result["reasons"])

    def test_large_gap_fails(self):
        result = MODULE.evaluate(trace(30, gap_ns=300_000_000))
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertIn("missing output cadence or gap over 250 ms", result["reasons"])

    def test_missing_eos_fails(self):
        result = MODULE.evaluate(trace(30, eos=False))
        self.assertEqual(result["decoder_gate"], "FAIL")

    def test_unsubmitted_output_is_rejected(self):
        events = trace(30)
        events.insert(-1, {"event": "output", "pts_us": 99_000_000, "mono_ns": 3_000_000_000})
        with self.assertRaisesRegex(ValueError, "absent from submitted"):
            MODULE.evaluate(events)


if __name__ == "__main__":
    unittest.main()
