"""CL-IMP-11 composed Type110/Type111 runtime lab acceptance."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from demo.cl_imp_11.dual_display_lab import run_lab  # noqa: E402


def test_dual_display_lab_runs_independent_streams_warning_failure_and_reconnect(tmp_path):
    output = tmp_path / "build" / "cl-imp-11"
    report = run_lab(output)

    assert report["status"] == "PASS"
    assert report["evidence"] == "MODEL_ONLY"
    assert report["display0"]["simultaneousIndependentFrames"] is True
    assert report["display0"]["warningPreemptionAndResume"] is True
    assert report["display0"]["secondaryFailureIsolation"] is True
    assert report["display0"]["primaryRemainedActive"] is True
    assert report["display0"]["rendererFrameBytes"] == 0
    assert report["display1"]["reconnectDemonstrated"] is True
    assert report["reconnect"] == {"generation1": 1, "generation2": 2, "passed": True}
    assert report["stockDelegation"] == "MOCK_ONLY"
    assert report["physicalScanout"] == "UNPROVEN"
    assert report["hondaIntegration"] == "DISABLED"
    assert report["iphoneAuthentication"] == "NOT_PERFORMED"
    assert set(report["resourcesAfterFinalClose"].values()) == {0, False}

    center = (output / "display0-type110-gen2-initial.png").read_bytes()
    cluster = (output / "display1-type111-gen2-initial.png").read_bytes()
    assert center.startswith(b"\x89PNG\r\n\x1a\n")
    assert cluster.startswith(b"\x89PNG\r\n\x1a\n")
    assert center != cluster
    assert (output / "display1-type111-gen1-resumed.png").exists()
    assert (output / "display0-type110-gen1-postfault.png").exists()
    assert not (output / "display1-type111-gen1-postfault.png").exists()
    page = (output / "index.html").read_text(encoding="utf-8")
    assert "NOT AUTHENTIC CARPLAY" in page
    assert "mock Type110 primary" in page
    saved = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert saved == report


def test_lab_replaces_only_its_known_artifacts(tmp_path):
    output = tmp_path / "build" / "cl-imp-11"
    output.mkdir(parents=True)
    unrelated = output / "operator-notes.txt"
    unrelated.write_text("preserve", encoding="utf-8")
    run_lab(output)
    assert unrelated.read_text(encoding="utf-8") == "preserve"


def test_lab_rejects_symlink_output_directory(tmp_path):
    target = tmp_path / "build" / "owned-output"
    target.mkdir(parents=True)
    link = tmp_path / "build" / "cl-imp-11"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        run_lab(link)
    assert list(target.iterdir()) == []
