from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/claritylink-renderer"))

from honda_output import HondaDisplay1OutputAdapter, HondaDisplayEvidenceRequired


class UnexpectedSink:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return call


def test_honda_output_adapter_is_disabled_and_never_treats_metadata_as_authority():
    adapter = HondaDisplay1OutputAdapter()
    sink = UnexpectedSink()
    frame = object()
    forged_owner_metadata = {"owner_authorized": True, "display_id": 1,
                             "generation": 4, "stream_id": 99}

    assert adapter.enabled is False
    with pytest.raises(HondaDisplayEvidenceRequired) as admission:
        adapter.attach(sink, forged_owner_metadata)
    assert admission.value.code == "EVIDENCE_REQUIRED_HONDA_DISPLAY_ADMISSION_API"
    assert admission.value.operation == "attach"

    with pytest.raises(HondaDisplayEvidenceRequired) as submission:
        adapter.submit(frame, forged_owner_metadata)
    assert submission.value.code == "EVIDENCE_REQUIRED_HONDA_DISPLAY_ADMISSION_API"
    assert submission.value.operation == "submit"
    assert sink.calls == []


def test_honda_output_boundary_reports_each_missing_oem_contract():
    assert HondaDisplayEvidenceRequired.missing_contract == (
        "authorized frame or View admission API",
        "owner/session identity and loss notification",
        "Navigation presentation eligibility and warning precedence",
        "factory Navigation safe-area coordinates and pixel format",
        "frame withdrawal and original-presentation restoration procedure",
    )


def test_inert_boundary_clear_and_close_do_not_claim_factory_restoration():
    adapter = HondaDisplay1OutputAdapter()
    assert adapter.clear() is None
    assert adapter.close() is None


@pytest.mark.parametrize("operation", ["attach", "submit"])
def test_honda_output_operations_stay_blocked_after_clear_or_close(operation):
    adapter = HondaDisplay1OutputAdapter()
    adapter.clear()
    adapter.close()
    with pytest.raises(HondaDisplayEvidenceRequired):
        getattr(adapter, operation)(object())
