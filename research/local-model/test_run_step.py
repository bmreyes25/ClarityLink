import importlib.util
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("run_step", Path(__file__).with_name("run_step.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PacketTests(unittest.TestCase):
    def test_step_packet_is_bounded_and_cited(self):
        prompt = MODULE.packet("F-B", "What is incomplete?")
        self.assertLessEqual(len(prompt), MODULE.MAX_CHARS)
        self.assertIn("SOURCE research/acquisition/FORENSIC_STATUS_20260925.md", prompt)
        self.assertIn("F-B. Acquire", prompt)

    def test_unknown_step_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.packet("13", "")


if __name__ == "__main__":
    unittest.main()
