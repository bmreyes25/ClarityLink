import json
from pathlib import Path
import unittest
from catalog_firmware import MEMBERS, STATES, catalog


class FirmwareCatalogTests(unittest.TestCase):
    def test_catalog_covers_allowlist_and_snapshots(self):
        data = json.loads(Path(__file__).with_name("firmware-catalog.json").read_text())
        self.assertEqual({(a["archive"].split("/")[-1], a["member"]) for a in data["artifacts"]},
                         {(archive, member) for archive, members in MEMBERS.items() for member in members})
        self.assertEqual([s["state"] for s in data["runtimeSnapshots"]], STATES)
        for item in data["artifacts"]:
            self.assertGreater(item["bytes"], 0)
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
        for snapshot in data["runtimeSnapshots"]:
            self.assertTrue(snapshot["audioFocusOwner"].startswith("unknown"))

    def test_original_dataset_is_rejected(self):
        with self.assertRaises(ValueError):
            catalog(Path("CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL"))
