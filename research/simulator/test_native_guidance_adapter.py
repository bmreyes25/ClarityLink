import unittest

from native_guidance_adapter import Guidance, expected_factory_view, render_events, stop_events


class NativeGuidanceAdapterTest(unittest.TestCase):
    def test_waze_positive_control_matches_observed_handler_distance(self):
        events = render_events(Guidance("start", "Example road", 81))
        self.assertEqual([event["handler"] for event in events], [5601, 5602, 5603])
        self.assertEqual(events[1]["turnSide"], 3)
        self.assertEqual(events[1]["event"], 1)
        self.assertEqual(events[2]["distanceMeters"], 81)

    def test_maneuver_mapping_matches_honda_hack_waze_branch(self):
        expected = {"left": (1, 4), "right": (2, 4), "straight": (3, 14)}
        for maneuver, (side, event) in expected.items():
            with self.subTest(maneuver=maneuver):
                turn = render_events(Guidance(maneuver, "Example road", 200))[1]
                self.assertEqual((turn["turnSide"], turn["event"]), (side, event))

    def test_saved_apple_maps_banner_cannot_invent_distance(self):
        with self.assertRaisesRegex(ValueError, "Verified distance"):
            render_events(Guidance("start", "Example Rd", None))

    def test_route_end_clears_status(self):
        self.assertEqual(stop_events(), [{"handler": 5601, "status": 2}])

    def test_ordinary_factory_views_omit_street_even_when_passed(self):
        self.assertEqual(expected_factory_view(Guidance("start", "Example road", 81)),
                         {"viewId": 61441, "streetVisible": False})
        self.assertEqual(expected_factory_view(Guidance("left", "Example road", 81)),
                         {"viewId": 61442, "streetVisible": False})


if __name__ == "__main__":
    unittest.main()
