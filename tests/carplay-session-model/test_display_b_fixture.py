import copy
import json
from pathlib import Path
import unittest


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "research" / "carplay" / "display-b-fixture.json"


class DisplayBFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text())

    def test_stock_primary_entry_is_logically_unchanged(self):
        stock = self.fixture["stock_primary_response"]
        augmented = self.fixture["augmented_response"]
        self.assertEqual(augmented["streams"][0], stock["streams"][0])
        self.assertEqual(augmented["streams"][0]["dataPort"], stock["streams"][0]["dataPort"])
        self.assertEqual(augmented["streams"][0]["display_uuid"], stock["streams"][0]["display_uuid"])

    def test_augmentation_adds_only_one_secondary_stream(self):
        stock_streams = self.fixture["stock_primary_response"]["streams"]
        augmented_streams = self.fixture["augmented_response"]["streams"]
        self.assertEqual(len(augmented_streams), len(stock_streams) + 1)
        self.assertEqual(augmented_streams[:-1], stock_streams)
        self.assertEqual(augmented_streams[-1]["type"], 111)

    def test_secondary_identity_and_port_are_distinct_fixture_tokens(self):
        primary = self.fixture["augmented_response"]["streams"][0]
        secondary = self.fixture["augmented_response"]["streams"][1]
        self.assertNotEqual(secondary["display_uuid"], primary["display_uuid"])
        self.assertNotEqual(secondary["dataPort"], primary["dataPort"])
        self.assertTrue(secondary["display_uuid"].startswith("FIXTURE_ONLY_"))
        self.assertTrue(secondary["dataPort"].startswith("FIXTURE_ONLY_"))

    def test_removing_augmentation_restores_stock_model_exactly(self):
        augmented = copy.deepcopy(self.fixture["augmented_response"])
        augmented["streams"].pop()
        self.assertEqual(augmented, self.fixture["stock_primary_response"])

    def test_unknown_fields_and_fixture_only_warning_are_explicit(self):
        self.assertIn("serializer", self.fixture["augmented_response"]["unknown_fields"])
        self.assertIn("primary_uuid_value_and_source", self.fixture["unknown_honda_fields"])
        self.assertIn("synthetic fixture values", self.fixture["stock_primary_response"]["streams"][0]["confidence"])


if __name__ == "__main__":
    unittest.main()
