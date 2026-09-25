import hashlib
import json
import pathlib
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
CAPTURE = ROOT.parent / "captures" / "20260918T153910Z-native-cluster-readonly"
VENDOR = ROOT.parent.parent / "extracted" / "system-vendor" / "system" / "vendor" / "media" / "mcs" / "j_config.xml"
METER = ROOT.parent / "resources" / "HondaHack" / "res" / "layout" / "meter_civic.xml"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DisplayProfileTest(unittest.TestCase):
    def test_profile_matches_working_firmware_and_captures(self):
        profile = json.loads((ROOT / "display-profile.json").read_text())
        vendor = ET.parse(ROOT / "working-backup" / "j_config.xml").getroot()
        meter = ET.parse(ROOT / "working-backup" / "meter_civic.xml").getroot()
        self.assertEqual(digest(ROOT / "working-backup" / "j_config.xml"), digest(VENDOR))
        self.assertEqual(digest(ROOT / "working-backup" / "meter_civic.xml"), digest(METER))
        self.assertEqual(profile["center"]["width"], int(vendor.find(".//VIDEO_WIDTH_PIXELS").attrib["Value"]))
        self.assertEqual(profile["center"]["height"], int(vendor.find(".//VIDEO_HEIGHT_PIXELS").attrib["Value"]))
        self.assertEqual(profile["meterLayout"]["width"], int(float(meter.attrib["{http://schemas.android.com/apk/res/android}layout_width"].removesuffix("px"))))
        self.assertEqual(profile["meterLayout"]["height"], int(float(meter.attrib["{http://schemas.android.com/apk/res/android}layout_height"].removesuffix("px"))))
        for name in ("center-maps.png", "center-music.png", "cluster-navigation.png"):
            self.assertEqual(digest(ROOT / "assets" / name), digest(CAPTURE / name))
            png = (ROOT / "assets" / name).read_bytes()
            self.assertEqual(struct.unpack(">II", png[16:24]), (800, 480))
        self.assertEqual(digest(CAPTURE / "cluster-maps.png"), digest(CAPTURE / "cluster-navigation.png"))


if __name__ == "__main__":
    unittest.main()
