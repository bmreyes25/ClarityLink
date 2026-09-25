import hashlib
import json
import pathlib
import subprocess
import unittest
import xml.etree.ElementTree as ET
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
RESEARCH = HERE.parent.parent
APK = HERE / "build/decoder-probe-signed.apk"
FIXTURE = HERE / "fixtures/avc-800x480-15fps.mp4"


class ProbeArtifactTest(unittest.TestCase):
    def test_fixed_clip_has_expected_size_and_frame_count(self):
        ffmpeg = RESEARCH / "tools/python/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
        result = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(FIXTURE),
                                 "-f", "null", "-"], capture_output=True, text=True, check=True)
        self.assertIn("800x480", result.stderr)
        self.assertIn("15 fps", result.stderr)
        self.assertIn("frame=   30", result.stderr)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                         "1a1f70418ad0df9210822ee03a44c313049879699ea75d9df3517dbcc42c04cc")

    def test_signed_apk_contains_uncompressed_fixture_and_no_permissions(self):
        with zipfile.ZipFile(APK) as archive:
            asset = archive.getinfo("assets/" + FIXTURE.name)
            self.assertEqual(asset.compress_type, zipfile.ZIP_STORED)
            self.assertEqual(archive.read(asset.filename), FIXTURE.read_bytes())
            self.assertGreater(len(archive.read("classes.dex")), 1000)
        root = ET.parse(HERE / "build/inspected/AndroidManifest.xml").getroot()
        self.assertEqual(root.attrib["package"], "org.claritylab.decoderprobe")
        self.assertEqual(root.findall("uses-permission"), [])
        info = (HERE / "build/inspected/apktool.yml").read_text()
        self.assertIn("minSdkVersion: 17", info)
        self.assertIn("targetSdkVersion: 17", info)

    def test_review_manifest_matches_all_final_inputs(self):
        record = json.loads((HERE / "PROBE-MANIFEST.json").read_text())
        paths = {
            "AndroidManifest.xml": HERE / "AndroidManifest.xml",
            "DecoderCapacityProbeActivity.java": HERE / "src/org/claritylab/decoderprobe/DecoderCapacityProbeActivity.java",
            "decoder-probe-signed.apk": APK,
        }
        for name, path in paths.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"][name])


if __name__ == "__main__":
    unittest.main()
