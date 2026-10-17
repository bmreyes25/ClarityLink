import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import pytest


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "tools/verify_api17_padded_crop_content.swift"


def test_padded_crop_verifier_requires_expected_green_control():
    source = VERIFIER.read_text()
    assert "negativeIsExpectedGreen = negative.allSatisfy" in source
    assert "Double($0[1]) > Double($0[0]) * 1.4" in source
    assert '"observedRoiRgb": negative' in source
    assert "usage: verify_api17_padded_crop_content.swift CROPPED.png NEGATIVE_CONTROL.png APK OUTPUT.json" in source


def _png(path: Path, rgb: tuple[int, int, int]) -> None:
    width, height = 800, 480
    pixel = bytes((*rgb, 255))
    row = b"\0" + pixel * width

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    content = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * height))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(content)


@pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("swift") is None,
    reason="AppKit screenshot verifier runtime is available only on macOS with Swift",
)
def test_padded_crop_verifier_accepts_green_and_rejects_blank_or_wrong_color(tmp_path):
    red = tmp_path / "cropped-red.png"
    _png(red, (240, 20, 10))
    apk = tmp_path / "lab.apk"
    apk.write_bytes(b"synthetic verifier input")

    green = tmp_path / "expected-green.png"
    _png(green, (20, 220, 30))
    receipt = tmp_path / "green-receipt.json"
    passed = subprocess.run(
        ["swift", str(VERIFIER), str(red), str(green), str(apk), str(receipt)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert passed.returncode == 0, passed.stderr
    result = json.loads(receipt.read_text())
    assert result["matches"] is True
    assert result["negativeControl"]["matchesExpectedGreen"] is True
    assert result["negativeControl"]["rejectedAsRed"] is True
    assert result["negativeControl"]["observedRoiRgb"]

    for name, color in (("black", (0, 0, 0)), ("blue", (20, 30, 230))):
        control = tmp_path / f"{name}.png"
        _png(control, color)
        rejected = subprocess.run(
            ["swift", str(VERIFIER), str(red), str(control), str(apk), str(tmp_path / f"{name}.json")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert rejected.returncode != 0, f"{name} negative control was accepted"
