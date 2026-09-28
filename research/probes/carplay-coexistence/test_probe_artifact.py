import hashlib
import json
import pathlib
import unittest
import xml.etree.ElementTree as ET
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
RESEARCH = HERE.parent.parent
APK = HERE / "build/carplay-coexistence-probe-signed.apk"
FIXTURE = RESEARCH / "probes/decoder-capacity/fixtures/avc-800x480-15fps.mp4"
SOURCE = HERE / "src/org/claritylab/carplaycoexistence/DecoderCoexistenceService.java"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class ProbeArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not APK.is_file():
            raise AssertionError("build signed probe first: python3 research/probes/carplay-coexistence/build_probe.py")

    def test_signed_apk_has_private_no_permission_background_service(self):
        with zipfile.ZipFile(APK) as archive:
            self.assertTrue(archive.read("AndroidManifest.xml").startswith(b"\x03\x00"))
            self.assertGreater(len(archive.read("classes.dex")), 1000)
            fixture_path = "assets/" + FIXTURE.name
            self.assertEqual(archive.getinfo(fixture_path).compress_type, zipfile.ZIP_STORED)
            self.assertEqual(archive.read(fixture_path), FIXTURE.read_bytes())
        manifest = ET.parse(HERE / "build/inspected/AndroidManifest.xml").getroot()
        self.assertEqual(manifest.attrib["package"], "org.claritylab.carplaycoexistence")
        self.assertEqual(manifest.findall("uses-permission"), [])
        service = manifest.find("application/service")
        self.assertIsNotNone(service)
        self.assertEqual(service.attrib[ANDROID_NS + "exported"], "true")
        self.assertEqual(service.attrib[ANDROID_NS + "name"], ".DecoderCoexistenceService")
        self.assertEqual(manifest.find("application/activity"), None)

    def test_service_is_bounded_and_never_creates_a_display_surface(self):
        source = SOURCE.read_text()
        for required in ("FRAMES = 900", "FPS = 15", "WIDTH = 800, HEIGHT = 480",
                         "DRAIN_LIMIT_NS = 5_000_000_000L", "startForeground(",
                         "System.nanoTime()", "BUFFER_FLAG_END_OF_STREAM",
                         "OMX.Nvidia.h264.decode", "status\\\":\\\"unavailable"):
            self.assertIn(required, source)
        for forbidden in ("new Surface(", "TextureView", "AudioTrack", "AudioManager",
                          "Socket(", "CAN", "su ", "INTERNET", "WRITE_SETTINGS"):
            self.assertNotIn(forbidden, source)
        self.assertNotRegex(source, r"System\.loadLibrary\(")

    def test_receipt_matches_source_apk_and_fixture(self):
        receipt = json.loads((HERE / "build/BUILD-RECEIPT.json").read_text())
        self.assertEqual(receipt["package"], "org.claritylab.carplaycoexistence")
        self.assertEqual(receipt["apk_sha256"], hashlib.sha256(APK.read_bytes()).hexdigest())
        self.assertEqual(receipt["service_source_sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(receipt["fixture_sha256"], hashlib.sha256(FIXTURE.read_bytes()).hexdigest())
        self.assertTrue(receipt["device_contacted"] is False)

    def test_apk_signature_verification_was_recorded_by_builder(self):
        receipt_text = (HERE / "build/BUILD-RECEIPT.json").read_text()
        self.assertIn("API-17 v1 signature verified", receipt_text)


if __name__ == "__main__":
    unittest.main()
