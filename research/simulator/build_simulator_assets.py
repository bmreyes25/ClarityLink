#!/usr/bin/env python3
"""Build local display metadata and file:// replay samples from copied evidence."""
import hashlib
import json
import pathlib
import struct
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
ANDROID = "{http://schemas.android.com/apk/res/android}"


def png_size(path):
    with path.open("rb") as source:
        header = source.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_profile():
    vendor_path = ROOT / "working-backup" / "j_config.xml"
    meter_path = ROOT / "working-backup" / "meter_civic.xml"
    vendor = ET.parse(vendor_path).getroot()
    meter = ET.parse(meter_path).getroot()
    width = int(vendor.find(".//VIDEO_WIDTH_PIXELS").attrib["Value"])
    height = int(vendor.find(".//VIDEO_HEIGHT_PIXELS").attrib["Value"])
    fps = int(vendor.find(".//MAX_FPS").attrib["Value"])
    meter_width = int(float(meter.attrib[ANDROID + "layout_width"].removesuffix("px")))
    meter_height = int(float(meter.attrib[ANDROID + "layout_height"].removesuffix("px")))
    files = {}
    for name in ("center-maps.png", "center-music.png", "cluster-navigation.png",
                 "center-20260925-native-maps.png", "cluster-20260925-native.png",
                 "center-20260925-cast-maps.png", "cluster-20260925-cast-maps.png",
                 "center-20260925-music.png", "cluster-20260925-cast-music.png",
                 "center-20260925-waze-route.png", "cluster-20260925-waze-route.png",
                 "center-20260925-honda-home.png", "center-20260925-waze-ended.png",
                 "cluster-20260925-waze-ended.png"):
        path = ROOT / "assets" / name
        size = png_size(path)
        if size != (width, height):
            raise ValueError(f"Unexpected {name} size: {size}")
        files[name] = {"sha256": sha256(path), "width": size[0], "height": size[1]}
    pairs = [
        ("observed-mirror-off", "20260925T150706Z-twin-off/twin-survey", "center-20260925-native-maps", "cluster-20260925-native"),
        ("observed-mirror-maps", "20260925T150706Z-twin-on/twin-survey", "center-20260925-cast-maps", "cluster-20260925-cast-maps"),
        ("observed-mirror-music", "20260925T150706Z-music-cast/music", "center-20260925-music", "cluster-20260925-cast-music"),
        ("observed-honda-waze", "20260925-waze-headunit-route/twin-survey", "center-20260925-waze-route", "cluster-20260925-waze-route"),
        ("observed-honda-home", "20260925-waze-background-home/twin-survey", "center-20260925-honda-home", "cluster-20260925-waze-route"),
        ("observed-honda-end", "20260925-waze-route-ended/twin-survey", "center-20260925-waze-ended", "cluster-20260925-waze-ended"),
    ]
    provenance = []
    for label, directory, center, cluster in pairs:
        pair = {"id": label, "evidence": "observed paired captures, consecutive not atomic",
                "timing": "sample tMs are replay order, not measured latency", "displays": {}}
        for display_id, side, capture_id in [(0, "center", center), (1, "hdmi", cluster)]:
            relative = f"research/captures/{directory}/display-{display_id}.png"
            source = ROOT.parents[1] / relative
            if sha256(source) != files[capture_id + ".png"]["sha256"]:
                raise ValueError(f"Capture copy mismatch: {label}/{side}")
            pair["displays"][side] = {"captureId": capture_id, "source": relative,
                                      "sha256": files[capture_id + ".png"]["sha256"]}
        provenance.append(pair)
    calibration = json.loads((ROOT / "photo-calibration.json").read_text())
    for registration in calibration["registrations"].values():
        for reference in (registration["frame"], registration["photo"]):
            if sha256(ROOT / reference["source"]) != reference["sha256"]:
                raise ValueError("Photo calibration source hash mismatch")
    if sha256(meter_path) != calibration["sourceCastRectangle"]["sha256"]:
        raise ValueError("Photo calibration layout hash mismatch")
    profile = {
        "source": "working copies of backed-up j_config.xml and Honda Hack meter_civic.xml; saved read-only display captures",
        "center": {"width": width, "height": height, "configuredMaxFps": fps},
        "clusterHdmiCapture": {"width": width, "height": height},
        "physicalNavigationBounds": {"rectangle": None, "evidence": "unknown safe edges; photo cast footprints are inferred separately",
                                     "calibrated": False, "source": "physicalClusterReferences"},
        "photoCalibration": {"source": "photo-calibration.json", "sha256": sha256(ROOT / "photo-calibration.json"),
                             "evidence": "inferred cast footprint per camera pose; physical safe bounds unknown"},
        "pairedCaptureProvenance": provenance,
        "meterLayout": {"width": meter_width, "height": meter_height,
                        "placementOnPhysicalCluster": "user reports cast in the NE compass/Navigation area; exact pixel boundary unmeasured"},
        "physicalClusterReferences": {
            name: {"image": "assets/" + name, "sha256": sha256(ROOT / "assets" / name)}
            for name in ("physical-cluster-20260925.jpg", "physical-maps-20260925.jpg",
                         "physical-carplay-home-20260925.jpg", "physical-music-20260925.jpg",
                         "physical-honda-home-20260925.jpg")
        },
        "physicalCastObservation": "wide central rectangle below speed and above Menu/trip row; speed/range visible; edge clearance near power/charge scales unverified",
        "files": files,
        "firmwareCopySha256": {"j_config.xml": sha256(vendor_path), "meter_civic.xml": sha256(meter_path)},
    }
    (ROOT / "display-profile.json").write_text(json.dumps(profile, indent=2) + "\n")


def make_samples():
    samples = {}
    for key, name in (("replay", "sample-replay.jsonl"),
                      ("dual", "sample-dual-screen.jsonl"),
                      ("captured", "sample-captured-pair.jsonl"),
                      ("liveCasting", "sample-live-casting-20260925.jsonl"),
                      ("wazeHeadunit", "sample-waze-headunit-20260925.jsonl"),
                      ("contract", "sample-contract-replay.jsonl"),
                      ("metadata", "sample-metadata-hypothesis.jsonl")):
        source = (ROOT / name).read_text()
        samples[key] = source
        for line in source.splitlines():
            if line.strip():
                json.loads(line)
    (ROOT / "samples.js").write_text("/* Generated by build_simulator_assets.py. */\nconst ClaritySamples = " + json.dumps(samples, separators=(",", ":")) + ";\n")
    calibration = json.loads((ROOT / "photo-calibration.json").read_text())
    (ROOT / "display-geometry.js").write_text("/* Generated numeric calibration; no pixels. */\nconst ClarityGeometry = " +
        json.dumps(calibration, separators=(",", ":")) + ";\n")


if __name__ == "__main__":
    make_profile()
    make_samples()
