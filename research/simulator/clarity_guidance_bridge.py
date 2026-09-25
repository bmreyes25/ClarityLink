#!/usr/bin/env python3
"""Apple Maps screenshot -> Honda Hack navigation card prototype.

Default mode only reads a local image and prints a display-update plan.
The bounded --live mode is for a later user-approved, stationary-car test.
It does not call factory Navigation setters or send vehicle-bus messages.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
OCR = ROOT / "guidance-ocr"
ACK = "I approve the stationary Clarity display test"


def interpret(banner):
    banner = " ".join(banner.split())
    rules = [
        (r"^Start on (.+)$", "start"),
        (r"^(?:Turn|Bear) left (?:onto|on) (.+)$", "left"),
        (r"^(?:Turn|Bear) right (?:onto|on) (.+)$", "right"),
        (r"^Continue (?:onto|on) (.+)$", "forward"),
    ]
    for pattern, icon in rules:
        match = re.fullmatch(pattern, banner, re.I)
        if match and 1 <= len(match.group(1)) <= 70:
            return {"icon": icon, "street": match.group(1), "distance": None,
                    "source": "Apple Maps screenshot OCR", "verified": False}
    return None


def ocr(image):
    if not OCR.is_file():
        raise RuntimeError("Build the offline GuidanceOCR.swift program first")
    proc = subprocess.run([str(OCR), str(image)], check=True, capture_output=True, text=True, timeout=45)
    result = json.loads(proc.stdout)
    if (result["width"], result["height"]) != (800, 480):
        raise ValueError("Uncalibrated CarPlay screen size")
    return result


def actions(candidate):
    if candidate is None:
        return []
    return [
        ["shell", "am", "broadcast", "-a", "cn.autohack.hondahack.UPDATE_NAVI_WAZE",
         "--es", "icon", candidate["icon"], "--es", "street", candidate["street"]],
    ]


STOP = ["shell", "am", "broadcast", "-a", "cn.autohack.hondahack.STOP_NAVI"]


def adb(serial, args, **kwargs):
    return subprocess.run(["adb", "-s", serial, *args], check=True, **kwargs)


def require_custom_meter_preferences(xml_text):
    """Refuse the old custom-view bridge when the live car uses native Waze mode."""
    root = ET.fromstring(xml_text)
    values = {item.get("name"): item.get("value") for item in root.findall("boolean")}
    if (values.get("nav_in_dashboard") != "true" or
            values.get("enable_custom_meter") != "true" or
            values.get("enable_screen_cast") != "false"):
        raise RuntimeError("Live Honda Hack preferences do not select the custom navigation view; bridge disabled")


def plan(image):
    reading = ocr(image)
    candidate = interpret(reading["bannerText"])
    return {"reading": reading["bannerText"], "candidate": candidate,
            "actions_after_approval": actions(candidate), "rollback": STOP,
            "scope": "Honda Hack navigation view only; no system-file patch",
            "limit": "Image-based, unverified; no distance or turn sent unless recognized"}


def live(serial, duration):
    prefs = adb(serial, ["shell", "su", "-c", "cat /data/data/cn.autohack.hondahack/shared_prefs/public.xml"],
                capture_output=True, text=True, timeout=10)
    require_custom_meter_preferences(prefs.stdout)
    end = time.monotonic() + duration
    last_banner = None
    last_change = time.monotonic()
    last_candidate = None
    showing = False
    with tempfile.TemporaryDirectory(prefix="clarity-bridge-", dir=ROOT.parent / "tmp") as scratch:
        frame = pathlib.Path(scratch) / "carplay.png"
        try:
            while time.monotonic() < end:
                with frame.open("wb") as out:
                    adb(serial, ["exec-out", "screencap", "-p"], stdout=out, timeout=10)
                reading = ocr(frame)
                if reading["bannerText"] != last_banner:
                    last_banner = reading["bannerText"]
                    last_change = time.monotonic()
                candidate = interpret(reading["bannerText"])
                fresh = time.monotonic() - last_change < 15
                if candidate and fresh:
                    key = (candidate["icon"], candidate["street"])
                    if key != last_candidate or not showing:
                        for action in actions(candidate):
                            adb(serial, action, capture_output=True, text=True, timeout=10)
                        showing, last_candidate = True, key
                elif showing:
                    adb(serial, STOP, capture_output=True, text=True, timeout=10)
                    showing, last_candidate = False, None
                time.sleep(2)
        finally:
            adb(serial, STOP, capture_output=True, text=True, timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=pathlib.Path, default=ROOT / "fixture-carplay-main.png")
    parser.add_argument("--live", action="store_true", help="later, approved vehicle display test only")
    parser.add_argument("--serial", help="explicit ADB serial for later approved test")
    parser.add_argument("--ack", help="explicit authorization phrase for later approved test")
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()
    if args.live:
        if args.ack != ACK or not args.serial or not 1 <= args.duration <= 120:
            parser.error("Live mode requires --serial, --ack with the exact phrase, and duration 1..120 seconds")
        live(args.serial, args.duration)
    else:
        print(json.dumps(plan(args.image), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, RuntimeError, ET.ParseError) as error:
        print(f"Bridge stopped: {error}", file=sys.stderr)
        sys.exit(1)
