import json
import pathlib
import unittest
from unittest.mock import patch

import clarity_guidance_bridge as bridge


class GuidanceBridgeTest(unittest.TestCase):
    def test_saved_apple_maps_reading_yields_visual_only_action(self):
        saved = json.loads((pathlib.Path(__file__).parent / "fixture-ocr.json").read_text())
        with patch.object(bridge, "ocr", return_value=saved):
            result = bridge.plan(pathlib.Path("unused.png"))
        self.assertEqual(result["candidate"]["street"], "Example Rd")
        self.assertEqual(result["actions_after_approval"][0][4], "cn.autohack.hondahack.UPDATE_NAVI_WAZE")
        self.assertNotIn("START_NAVI", str(result))
        self.assertEqual(result["rollback"], bridge.STOP)

    def test_unknown_banner_never_sends_a_turn(self):
        self.assertIsNone(bridge.interpret("Are You Gonna Go My Way"))
        self.assertEqual(bridge.actions(None), [])

    def test_ocr_process_has_finite_timeout(self):
        with patch.object(bridge.subprocess, "run", return_value=type("Result", (), {"stdout": '{"width":800,"height":480,"bannerText":"Start on Example Rd"}'})()) as run:
            bridge.ocr(pathlib.Path("unused.png"))
        self.assertEqual(run.call_args.kwargs["timeout"], 45)

    def test_live_bridge_refuses_observed_native_waze_mode(self):
        xml = ('<map><boolean name="nav_in_dashboard" value="true"/>'
               '<boolean name="enable_custom_meter" value="false"/>'
               '<boolean name="enable_screen_cast" value="true"/></map>')
        with self.assertRaisesRegex(RuntimeError, "bridge disabled"):
            bridge.require_custom_meter_preferences(xml)

    def test_live_bridge_accepts_only_custom_view_mode(self):
        xml = ('<map><boolean name="nav_in_dashboard" value="true"/>'
               '<boolean name="enable_custom_meter" value="true"/>'
               '<boolean name="enable_screen_cast" value="false"/></map>')
        bridge.require_custom_meter_preferences(xml)


if __name__ == "__main__":
    unittest.main()
