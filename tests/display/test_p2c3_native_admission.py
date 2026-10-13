"""Host-only negative interface stubs; they never connect to Honda Binder."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "research/architecture/p2c3-native-display-matrix.json"


class ControlOnlyBinderStub:
    """Model only the reviewed control/status capability, not unknown grants."""

    def __init__(self, caller_admitted=False):
        self.caller_admitted = caller_admitted
        self.status_reads = 0

    def read_status(self):
        if not self.caller_admitted:
            raise PermissionError("caller admission unproved or denied")
        self.status_reads += 1
        return {"synthetic": True, "lvds_active": False}

    def submit_surface(self, _surface):
        raise NotImplementedError("reviewed Honda Binder has no Surface transaction")


def test_unknown_or_denied_caller_cannot_use_control_interface():
    stub = ControlOnlyBinderStub()
    with pytest.raises(PermissionError):
        stub.read_status()
    assert stub.status_reads == 0


def test_admitted_control_caller_still_has_no_pixel_submission():
    stub = ControlOnlyBinderStub(caller_admitted=True)
    assert stub.read_status()["synthetic"] is True
    with pytest.raises(NotImplementedError):
        stub.submit_surface(object())
    assert stub.status_reads == 1


def test_matrix_keeps_content_and_admission_unknowns_explicit():
    matrix = json.loads(MATRIX.read_text())
    assert matrix["supported_external_pixel_sink_found"] is False
    assert [item["rank"] for item in matrix["candidates"]] == [1, 2, 3, 4, 5]
    for candidate in matrix["candidates"]:
        assert candidate["classification"] != "SUPPORTED"
        assert candidate["evidence"] and candidate["blocker"] and candidate["decisive_evidence"]
        assert candidate["warning_precedence"] and candidate["crash_restoration"]
    binder = matrix["candidates"][0]
    assert binder["classification"] == "CONTROL_ONLY"
    assert "no reviewed Surface" in binder["data_format"]
