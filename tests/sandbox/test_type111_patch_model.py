"""R5X synthetic behavior and scope tests; no receiver or device fixtures."""

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-sandbox"))

from type111_patch_model import (  # noqa: E402
    MODEL_LABELS,
    MockDisplaySink,
    PatchDecision,
    PatchError,
    SetupRequest,
    StreamDescriptor,
    TheoreticalPatchSandbox,
    Type110PrimaryScreen,
    Type111Listener,
    validate_model_artifact_name,
)


@pytest.fixture
def inputs():
    primary = Type110PrimaryScreen(
        StreamDescriptor(110, "SYNTHETIC-110"), b"SYNTHETIC:opaque-stock-response"
    )
    request = SetupRequest("SYNTHETIC-session", 7, primary.descriptor)
    return request, primary


def setup_secondary(inputs):
    request, primary = inputs
    return TheoreticalPatchSandbox().receive_setup(
        request, primary, enable_type111=True, request_type111=True
    )


def test_type110_preserved_without_type111(inputs):
    request, primary = inputs
    session = TheoreticalPatchSandbox().receive_setup(request, primary)
    assert session.response.streams == (primary.descriptor,)
    assert session.primary is primary
    assert session.primary.opaque_stock_model == b"SYNTHETIC:opaque-stock-response"
    assert session.secondary is None
    assert session.decision is PatchDecision.STOCK_ONLY


def test_type111_adds_separate_synthetic_response(inputs):
    session = setup_secondary(inputs)
    assert session.response.streams[0] is inputs[1].descriptor
    assert session.response.streams[1].stream_type == 111
    assert session.response.streams[1].connection_id != inputs[1].descriptor.connection_id
    assert session.response.evidence == "MODEL_ONLY"


def test_type111_listener_bound_to_session_generation(inputs):
    session = setup_secondary(inputs)
    assert session.secondary.listener.generation == session.generation
    assert session.secondary.generation == session.generation
    assert session.secondary.listener.transport == "MOCK_ONLY"
    assert session.secondary.descriptor.data_port == 40007


@pytest.mark.parametrize("failure", ["listener", "augmentation"])
def test_type111_failure_does_not_destroy_type110(inputs, failure):
    request, primary = inputs
    session = TheoreticalPatchSandbox().receive_setup(
        request, primary, enable_type111=True, request_type111=True, fail_at=failure
    )
    assert session.primary is primary
    assert session.response.streams == (primary.descriptor,)
    assert session.secondary is None
    assert not session.closed


def test_teardown_cleans_type111_resources(inputs):
    session = setup_secondary(inputs)
    child = session.secondary
    assert TheoreticalPatchSandbox().teardown_manager.teardown(session, 7)
    assert not child.active
    assert not child.listener.open
    assert not child.security.active
    assert not child.decoder.active
    assert child.display.displayed is None
    assert session.primary is inputs[1]


def test_teardown_idempotent(inputs):
    session = setup_secondary(inputs)
    manager = TheoreticalPatchSandbox().teardown_manager
    assert not manager.teardown(session, 6)
    assert session.secondary.listener.open
    assert manager.teardown(session, 7)
    assert not manager.teardown(session, 7)


def test_mock_display_clears_on_teardown(inputs):
    sandbox = TheoreticalPatchSandbox()
    session = setup_secondary(inputs)
    assert sandbox.deliver_mock_frame(session, 7, "MOCK_FRAME:turn-left")
    assert session.secondary.display.displayed == "MOCK_DECODED:turn-left"
    assert sandbox.teardown_manager.teardown(session, 7)
    assert session.secondary.display.displayed is None
    assert session.secondary.display.clear_reason == "teardown"


def test_stale_frame_suppressed(inputs):
    sandbox = TheoreticalPatchSandbox()
    session = setup_secondary(inputs)
    assert sandbox.deliver_mock_frame(session, 7, "MOCK_FRAME:turn-left")
    assert not sandbox.deliver_mock_frame(session, 6, "MOCK_FRAME:stale")
    assert session.secondary.display.displayed is None
    assert session.secondary.display.clear_reason == "stale"
    sandbox.lose_source(session)
    assert session.secondary.display.clear_reason == "lost"


def test_no_deployable_artifacts_created(tmp_path):
    before = list(tmp_path.iterdir())
    for name in ("receiver.bin", "receiver.patch", "receiver.so", "receiver.apk", "receiver.img"):
        with pytest.raises(PatchError):
            validate_model_artifact_name(name)
    assert list(tmp_path.iterdir()) == before
    assert validate_model_artifact_name("notes.txt").name == "notes.txt"


def test_model_labels_include_not_deployable():
    assert MODEL_LABELS == {
        "MODEL_ONLY", "NOT_DEPLOYABLE", "NOT_HONDA_BINARY",
        "NOT_REAL_CARPLAY", "NOT_MFI", "NO_REAL_JMCS_PATCH",
    }


def test_attempt_type111_without_explicit_enable_flag(inputs):
    with pytest.raises(PatchError, match="explicit model enable"):
        TheoreticalPatchSandbox().receive_setup(*inputs, request_type111=True)


def test_attempt_real_honda_path(inputs):
    with pytest.raises(PatchError):
        SetupRequest("SYNTHETIC-session", 7, inputs[1].descriptor, source="/system/bin/jmcs")
    with pytest.raises(PatchError):
        validate_model_artifact_name("/system/bin/jmcs")


def test_attempt_real_socket_or_listener():
    with pytest.raises(PatchError):
        Type111Listener(7, 40007, transport="TCP")


def test_attempt_deployable_patch_artifact():
    with pytest.raises(PatchError):
        validate_model_artifact_name("real_jmcs_patch.patch")


def test_static_dependency_boundary():
    source = (ROOT / "src" / "claritylink-sandbox" / "type111_patch_model.py").read_text()
    for forbidden in ("import socket", "import subprocess", "import ctypes", "import os", "open(", "write_bytes(", "connect(", "bind("):
        assert forbidden not in source
