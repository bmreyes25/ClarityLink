import json
import unittest
from pathlib import Path


class ForensicStorageFixtureTests(unittest.TestCase):
    def test_sanitized_gpt_fixture_is_consistent_with_mounts(self):
        fixture = json.loads(Path(__file__).with_name("forensic-storage-map.json").read_text())
        self.assertEqual(fixture["image_bytes"], 7_549_747_200)
        partitions = fixture["partitions"]
        self.assertEqual(len(partitions), 9)
        self.assertEqual([p["index"] for p in partitions], list(range(1, 10)))
        self.assertTrue(all(p["ext4_superblock_signature"] for p in partitions))
        for previous, current in zip(partitions, partitions[1:]):
            self.assertLess(previous["end_lba"], current["start_lba"])
        self.assertEqual({p["name"]: p["mount"]["path"] for p in partitions}, {
            "CAC": "/cache", "CAP": "/system/vendor", "APP": "/system", "LOG": "/log",
            "MITSU": "/data/MitsubishiElectric", "SDA": "/mnt/data1", "SDA2": "/mnt/data2",
            "SDC": "/mnt/media", "UDA": "/data",
        })
        self.assertTrue(next(p for p in partitions if p["name"] == "APP")["mount"]["read_only"])
        self.assertFalse(next(p for p in partitions if p["name"] == "UDA")["mount"]["read_only"])
        self.assertIn("non-atomic", fixture["source"])


if __name__ == "__main__":
    unittest.main()
