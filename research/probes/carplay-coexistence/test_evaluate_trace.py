import importlib.util
import importlib
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("evaluate_trace", Path(__file__).with_name("evaluate_trace.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
EXTRACTOR = importlib.import_module("extract_logcat")


def trace(produced=30, gap_ns=66_666_667, eos=True, planned=30, input_gap_ns=66_666_667,
          start_delay_ns=0):
    duration_ms = 60000 if planned == 900 else (planned * 1000 // 15)
    events = [{"event": "start", "planned_frames": planned, "duration_ms": duration_ms,
               "width": 800, "height": 480, "fps": 15,
               "codec": "OMX.Nvidia.h264.decode", "mono_ns": 0},
              {"event": "format", "width": 800, "height": 480}]
    timed = []
    for i in range(planned):
        timed.append({"event": "input", "pts_us": i * 66_667,
                      "mono_ns": start_delay_ns + i * input_gap_ns + 1})
        if i < produced:
            timed.append({"event": "output", "pts_us": i * 66_667,
                          "mono_ns": start_delay_ns + i * gap_ns + input_gap_ns // 2})
    events.extend(sorted(timed, key=lambda event: event["mono_ns"]))
    if eos:
        events.append({"event": "eos", "confirmed": True})
    return events


class TraceTests(unittest.TestCase):
    def test_old_28_of_30_result_is_below_95_percent(self):
        result = MODULE.evaluate(trace(28))
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertEqual(result["required_output"], 29)
        self.assertEqual(result["output_percent"], 93.33)

    def test_29_of_30_passes_sample_quality_but_not_full_duration_gate(self):
        result = MODULE.evaluate(trace(29))
        self.assertEqual(result["sample_quality_gate"], "PASS")
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertFalse(result["full_duration_ok"])
        self.assertIn("UNOBSERVED", result["carplay_picture_voice_verdict"])

    def test_855_of_900_is_exact_60_second_threshold(self):
        result = MODULE.evaluate(trace(855, planned=900))
        self.assertEqual(result["required_output"], 855)
        self.assertEqual(result["decoder_gate"], "PASS")
        self.assertTrue(result["full_duration_ok"])

    def test_fast_submitted_run_does_not_count_as_60_seconds(self):
        result = MODULE.evaluate(trace(900, planned=900, input_gap_ns=1_000_000))
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertIn("input run shorter than planned duration", result["reasons"])

    def test_late_first_input_does_not_shift_the_duration_window(self):
        result = MODULE.evaluate(trace(900, planned=900, start_delay_ns=1_000_000_000))
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertIn("first input started too late", result["reasons"])

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
        with self.assertRaisesRegex(ValueError, "not submitted before output"):
            MODULE.evaluate(events)

    def test_output_cannot_precede_its_input(self):
        events = trace(30)
        input_index = next(i for i, event in enumerate(events) if event.get("event") == "input")
        output_index = next(i for i, event in enumerate(events) if event.get("event") == "output")
        events[input_index], events[output_index] = events[output_index], events[input_index]
        with self.assertRaisesRegex(ValueError, "submitted before output"):
            MODULE.evaluate(events)

    def test_unconfirmed_eos_is_not_a_pass(self):
        events = trace(30)
        events[-1]["confirmed"] = False
        result = MODULE.evaluate(events)
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertIn("EOS/drain not confirmed", result["reasons"])

    def test_software_codec_is_not_hardware_coexistence_evidence(self):
        events = trace(30)
        events[0]["codec"] = "OMX.google.h264.decoder"
        result = MODULE.evaluate(events)
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertIn("NVIDIA hardware decoder identity not confirmed", result["reasons"])

    def test_wrong_later_format_invalidates_format_confirmation(self):
        events = trace(30)
        events.insert(-1, {"event": "format", "width": 640, "height": 360})
        result = MODULE.evaluate(events)
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertFalse(result["format_ok"])

    def test_codec_error_fails_even_when_frame_count_passes(self):
        events = trace(30)
        events.insert(-1, {"event": "error", "message": "synthetic codec failure"})
        result = MODULE.evaluate(events)
        self.assertEqual(result["decoder_gate"], "FAIL")
        self.assertIn("codec error", result["reasons"])

    def test_outputs_after_eos_are_rejected(self):
        events = trace(29)
        eos_index = next(i for i, event in enumerate(events) if event.get("event") == "eos")
        events.insert(eos_index + 1, {"event": "output", "pts_us": 0, "mono_ns": 9_000_000_000})
        with self.assertRaisesRegex(ValueError, "after EOS"):
            MODULE.evaluate(events)

    def test_logcat_extractor_keeps_json_events_and_ignores_other_tags(self):
        events = trace(29)
        raw = "".join("09-28 12:00:00.000 I/ClarityCoexistence( 123): " +
                       __import__("json").dumps(event) + "\n" for event in events)
        raw += "09-28 12:00:00.001 I/OtherTag( 123): noise\n"
        extracted = EXTRACTOR.extract(raw)
        self.assertEqual(extracted, events)
        self.assertEqual(MODULE.evaluate(extracted)["sample_quality_gate"], "PASS")
        self.assertEqual(MODULE.evaluate(extracted)["decoder_gate"], "FAIL")


if __name__ == "__main__":
    unittest.main()
