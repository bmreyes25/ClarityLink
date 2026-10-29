"""CL-INGEST-HARDEN-02 (issue #96): one failure-handling order across the whole Type111 error path.

Offline and synthetic. Every error path must (1) withdraw host content, (2) run each
independent cleanup step, and only then (3) record diagnostics on a best-effort basis.
Diagnostic extraction or storage failing must never leave project content visible.
Nothing here is evidence about a Honda or a real iPhone.
"""
import pytest

import t111_synth as synth
import type111_ingest
from claritylink_jmcs.display import DisplayError
from claritylink_jmcs.receiver import ReceiverError, ReceiverState
from test_cl_ingest_harden_01_sink_fail_closed import (  # noqa: F401 - fixtures and helpers
    HostileNameError, assert_sink_closed, decoded, hostile_names, make, raiser, shown, stream)
from type111_ingest import Fault, SinkRejection

start_type111 = synth.start_type111


class FailingList(list):
    """A diagnostic log whose append fails, as under memory pressure."""

    def append(self, _item):
        raise MemoryError("diagnostic log full")


class UnreadableCodeError(ReceiverError):
    """A ReceiverError whose ``code`` cannot be read."""

    def __init__(self):
        RuntimeError.__init__(self, "unreadable")

    @property
    def code(self):
        raise RuntimeError("code lookup failed")


@pytest.fixture
def streaming(make, stream):
    """A pipeline with one frame presented through the real receiver path."""
    pipe = make()
    client = start_type111(pipe)
    client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
    assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
    assert pipe.host.visible_content is not None
    yield pipe, client
    client.close()


def assert_withdrawn(pipe):
    assert pipe.host.visible_content is None and pipe.output.last_bound is None
    assert pipe.host.residual_state == ()


# ---- A / B / P: receiver exceptions reach fault handling whatever their diagnostics do ----
def test_receiver_exception_with_hostile_type_name_withdraws_content(streaming, monkeypatch):
    pipe, _client = streaming
    generation = pipe.receiver.stream_identity(111).stream_generation
    monkeypatch.setattr(pipe.receiver, "receive_secondary_frame", raiser_exact(HostileNameError("boom")))
    with hostile_names():
        outcome = pipe.pump_frame()  # must not raise
    assert not outcome.accepted and outcome.fault is Fault.RECEIVER_DEATH
    assert outcome.code == "receiver_exception:unnamed_exception"
    assert_withdrawn(pipe)
    with pytest.raises(DisplayError, match="output_inactive"):
        pipe.output.show(decoded(generation, 99))


def raiser_exact(exc):
    def fail(*_args, **_kwargs):
        raise exc
    return fail


def test_receiver_error_with_unreadable_code_takes_the_conservative_fault_path(streaming, monkeypatch):
    pipe, _client = streaming
    monkeypatch.setattr(pipe.receiver, "receive_secondary_frame", raiser_exact(UnreadableCodeError()))
    outcome = pipe.pump_frame()
    assert not outcome.accepted and outcome.fault is Fault.TYPE111_TRANSPORT_FAILURE
    assert outcome.code == "receiver_error_unreadable"
    assert_withdrawn(pipe)


def test_receiver_error_with_a_valid_code_keeps_its_code_and_taxonomy(streaming, monkeypatch):
    pipe, _client = streaming
    monkeypatch.setattr(pipe.receiver, "receive_secondary_frame", raiser_exact(ReceiverError("decode_failed")))
    outcome = pipe.pump_frame()
    assert outcome.code == "decode_failed" and outcome.fault is Fault.DECODER_DEATH
    assert_withdrawn(pipe)


# ---- C / D: rejection and cleanup bookkeeping can fail without leaving content visible ----
def test_rejection_bookkeeping_failure_cannot_leave_content_visible(shown, monkeypatch):
    pipe, generation = shown
    pipe.output.rejected = FailingList()
    observed = []
    with pytest.raises(SinkRejection, match="stale_stream_generation"):
        try:
            pipe.output.show(decoded(generation + 1, 2))
        finally:
            observed.append(pipe.host.visible_content)
    assert observed == [None]
    assert pipe.output.diagnostics_dropped == 1
    assert_sink_closed(pipe, generation)


def test_rejection_bookkeeping_failure_on_an_unexpected_error_keeps_the_cause(shown, monkeypatch):
    pipe, generation = shown
    pipe.output.rejected = FailingList()
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser())
    with pytest.raises(SinkRejection) as caught:
        pipe.output.show(decoded(generation, 2))
    assert isinstance(caught.value.__cause__, RuntimeError) and str(caught.value.__cause__) == "injected"
    assert pipe.host.visible_content is None
    monkeypatch.undo()
    assert_sink_closed(pipe, generation)


def test_cleanup_failure_bookkeeping_failure_is_survived_and_the_failed_withdrawal_stays_reported(
        shown, monkeypatch):
    pipe, generation = shown
    pipe.output.cleanup_failures = FailingList()
    monkeypatch.setattr(pipe.host, "revoke", raiser("host unavailable", OSError))
    with pytest.raises(SinkRejection, match="stale_stream_generation") as caught:
        pipe.output.show(decoded(generation + 1, 2))
    assert isinstance(caught.value.cleanup_error, OSError)
    assert pipe.output.withdrawal_pending  # never claimed empty: the host refused
    assert pipe.output.diagnostics_dropped == 1
    monkeypatch.undo()
    pipe.output.clear()
    assert not pipe.output.withdrawal_pending and pipe.host.visible_content is None


# ---- E / F / G / H: pipeline fault handling runs every independent step ----
def test_fault_record_append_failure_does_not_block_withdrawal_or_cleanup(streaming):
    pipe, _client = streaming
    pipe.faults = FailingList()
    report = pipe.end_type111()  # must not raise
    assert report is not None and pipe.diagnostics_dropped >= 1
    assert_withdrawn(pipe)
    assert pipe.receiver.secondary is None and not pipe.output.inside_show()


def test_cleanup_failure_append_failure_does_not_block_receiver_cleanup(streaming, monkeypatch):
    pipe, _client = streaming
    pipe.cleanup_failures = FailingList()
    monkeypatch.setattr(pipe.output, "fail_closed", raiser("sink broke", OSError))
    pipe.end_type111()
    assert pipe.host.visible_content is None  # the coordinator's own revoke still withdrew it
    assert pipe.receiver.secondary is None and pipe.diagnostics_dropped >= 1


def test_host_revoke_failure_is_reported_and_never_claimed_clean(streaming, monkeypatch):
    pipe, _client = streaming
    monkeypatch.setattr(pipe.host, "revoke", raiser("host unavailable", OSError))
    pipe.end_type111()  # must not raise
    assert pipe.faults[-1].cleanup_ok is False
    assert pipe.output.withdrawal_pending and "withdrawal_pending" in pipe.residual()
    assert pipe.host.visible_content is not None  # truthfully still visible: the host refused
    monkeypatch.undo()
    pipe.output.clear()
    assert pipe.host.visible_content is None


def test_coordinator_fault_failure_still_withdraws_and_closes_the_receiver_stream(streaming, monkeypatch):
    pipe, _client = streaming
    monkeypatch.setattr(pipe.coordinator, "fault", raiser("coordinator broke"))
    report = pipe.end_type111()  # must not raise
    assert report.failed == ("coordinator",)
    assert pipe.faults[-1].cleanup_ok is False and pipe.cleanup_failures == ["RuntimeError"]
    assert pipe.host.visible_content is None  # the sink withdrew before the coordinator was asked
    assert pipe.receiver.secondary is None and pipe.receiver.decoder is None


def test_receiver_teardown_failure_is_reported_and_the_secondary_is_still_released(streaming, monkeypatch):
    pipe, _client = streaming
    monkeypatch.setattr(pipe.receiver, "teardown", raiser("teardown broke"))
    pipe.disconnect()  # must not raise
    assert pipe.faults[-1].cleanup_ok is False and "RuntimeError" in pipe.cleanup_failures
    assert_withdrawn(pipe)
    assert pipe.receiver.secondary is None  # independent step ran despite the teardown failure
    monkeypatch.undo()
    pipe.disconnect()  # R: repeating the disconnect completes the teardown
    assert pipe.faults[-1].cleanup_ok is True and pipe.session_residual() == ()


def test_repeated_disconnect_after_a_clean_one_is_idempotent(streaming):
    pipe, _client = streaming
    pipe.disconnect()
    first = pipe.cleanup_failures[:]
    pipe.disconnect()
    assert pipe.cleanup_failures == first and pipe.faults[-1].cleanup_ok is True
    assert_withdrawn(pipe)
    assert pipe.residual() == ()


def test_settle_survives_a_coordinator_sync_failure_and_still_finishes_cleanup(streaming, monkeypatch):
    pipe, _client = streaming
    pipe.host.revoke("host timer expired")  # the host alone withdrew; the coordinator still holds a lease
    monkeypatch.setattr(pipe.coordinator, "sync", raiser("sync broke"))
    assert pipe.settle() is True  # must not raise
    assert pipe.faults[-1].cleanup_ok is False and pipe.receiver.secondary is None
    assert pipe.output.last_bound is None


# ---- S: a Type111 fault never takes Type110 down ----
def test_type110_survives_a_type111_scoped_fault_with_unreadable_diagnostics(make, stream, monkeypatch):
    pipe = make()
    client, primary = start_type111(pipe, with_primary=True)
    primary.sendall(stream.primary_message(0))
    pipe.receiver.receive_primary_frame(pipe.generation)
    held, decoder = pipe.primary_display.current, pipe.receiver.primary_decoder
    client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
    assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
    monkeypatch.setattr(pipe.receiver, "receive_secondary_frame", raiser_exact(UnreadableCodeError()))
    assert pipe.pump_frame().fault is Fault.TYPE111_TRANSPORT_FAILURE  # Type111-scoped, not RECEIVER_DEATH
    monkeypatch.undo()
    assert pipe.host.visible_content is None
    assert pipe.primary_display.current is held and not decoder.closed
    assert pipe.receiver.state is not ReceiverState.FAILED
    primary.sendall(stream.primary_message(1))
    assert pipe.receiver.receive_primary_frame(pipe.generation).startswith(b"\x89PNG")
    client.close()
    primary.close()


# ---- ECC review follow-ups: expiry, setup, str-subclass codes, truthful return value ----
def test_expiry_whose_withdrawal_fails_is_reported_and_still_cleans_up(streaming, monkeypatch):
    pipe, _client = streaming
    pipe.host._clock.advance(10.0)  # lease expired; the host applies it inside the next lease read
    monkeypatch.setattr(pipe.host._cluster, "withdraw_main", raiser("revoke broke", OSError))
    assert pipe.settle() is True  # must not raise
    assert pipe.faults[-1].cleanup_ok is False and "OSError" in pipe.cleanup_failures
    assert pipe.receiver.secondary is None and pipe.output.last_bound is None
    assert pipe.output.withdrawal_pending  # never claimed empty: the host refused


@pytest.mark.parametrize("error", [OSError("listener broke"), UnreadableCodeError()])
def test_setup_failure_of_any_kind_releases_the_half_built_stream(make, monkeypatch, error):
    pipe = make()
    pipe.open_session()
    real_setup = pipe.receiver.setup

    def setup_then_fail(*args, **kwargs):
        real_setup(*args, **kwargs)
        raise error

    monkeypatch.setattr(pipe.receiver, "setup", setup_then_fail)
    outcome = pipe.setup_type111(12)  # must not raise
    assert not outcome.accepted and outcome.fault is Fault.INIT_FAILURE
    assert pipe.receiver.secondary is None and pipe.receiver.decoder is None
    assert pipe.faults[-1].kind is Fault.INIT_FAILURE


class HostileStr(str):
    def __hash__(self):
        raise RuntimeError("hash broke")

    def __format__(self, _spec):
        raise RuntimeError("format broke")


def test_str_subclass_receiver_code_cannot_block_the_fault_path(streaming, monkeypatch):
    pipe, _client = streaming
    error = ReceiverError("placeholder")
    error.code = HostileStr("socket_read_failed")
    monkeypatch.setattr(pipe.receiver, "receive_secondary_frame", raiser_exact(error))
    outcome = pipe.pump_frame()  # must not raise
    assert outcome.code == "socket_read_failed" and type(outcome.code) is str
    assert outcome.fault is Fault.TYPE111_TRANSPORT_FAILURE
    assert_withdrawn(pipe)


def test_returned_report_does_not_claim_success_when_cleanup_failed(streaming, monkeypatch):
    pipe, _client = streaming
    monkeypatch.setattr(pipe.receiver, "teardown", raiser("teardown broke"))
    report = pipe.disconnect()
    assert "receiver_cleanup" in report.failed
    monkeypatch.undo()
    monkeypatch.setattr(pipe.output, "fail_closed", raiser("sink broke", OSError))
    assert "withdrawal" in pipe.disconnect().failed
