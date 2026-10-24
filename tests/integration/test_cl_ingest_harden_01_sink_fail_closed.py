"""CL-INGEST-HARDEN-01 (issue #96): LeaseGatedOutput.show() must fail closed on ANY ordinary error.

Offline and synthetic. A direct ``show()`` caller, with no pipeline-level exception
handling in front of it, must find the simulated Display 1 host empty and the output
inactive by the time an unexpected error reaches it. Nothing here is evidence about a
Honda or a real iPhone.
"""
import threading

import pytest

import t111_synth as synth
import type111_ingest
from claritylink_jmcs.decoder import DecodedFrame
from claritylink_jmcs.display import DisplayError
from claritylink_jmcs.frames import FrameError
from claritylink_jmcs.receiver import ReceiverState
from type111_ingest import Type111IngestPipeline

start_type111 = synth.start_type111
WAIT_SECONDS = 5.0


@pytest.fixture(scope="module")
def stream():
    return synth.SyntheticStream(4)


@pytest.fixture
def make():
    created = []

    def factory(**kwargs):
        receiver_kwargs = dict(synth.DIMENSIONS)
        pipe = Type111IngestPipeline(lab_mode=True, clock=synth.Clock(), receiver_kwargs=receiver_kwargs, **kwargs)
        created.append(pipe)
        return pipe

    yield factory
    for pipe in created:
        pipe.receiver.teardown(pipe.generation)


@pytest.fixture
def shown(make):
    """A pipeline whose Type111 output has already presented one valid frame."""
    pipe = make()
    pipe.open_session()
    assert pipe.setup_type111(12).accepted
    generation = pipe.receiver.stream_identity(111).stream_generation
    pipe.output.show(decoded(generation, 1, (1, 2, 3)))
    assert pipe.host.visible_content is not None
    return pipe, generation


def decoded(generation, timestamp, rgb=(4, 5, 6)):
    return DecodedFrame(synth.make_png(synth.WIDTH, synth.HEIGHT, rgb), timestamp, generation,
                        synth.WIDTH, synth.HEIGHT)


def raiser(message="injected", error=RuntimeError):
    def fail(*_args, **_kwargs):
        raise error(message)
    return fail


def assert_sink_closed(pipe, generation):
    assert pipe.host.visible_content is None
    assert pipe.output.last_bound is None
    accepted = pipe.output.accepted
    with pytest.raises(DisplayError, match="output_inactive"):
        pipe.output.show(decoded(generation, 99))
    assert pipe.output.accepted == accepted and pipe.host.visible_content is None


# ---- injection points: each is reached with project content already on the host ----
INJECTIONS = {
    "conversion": lambda pipe, mp: mp.setattr(type111_ingest, "png_to_rgb24", raiser()),
    "video_frame_construction": lambda pipe, mp: mp.setattr(type111_ingest, "VideoFrame", raiser()),
    "frame_binding": lambda pipe, mp: mp.setattr(type111_ingest, "LeaseBoundFrame", raiser()),
    "coordinator_submission": lambda pipe, mp: mp.setattr(pipe.coordinator, "submit_frame", raiser()),
}


@pytest.mark.parametrize("point", sorted(INJECTIONS))
def test_unexpected_error_withdraws_prior_content_before_the_caller_sees_it(shown, monkeypatch, point):
    pipe, generation = shown
    INJECTIONS[point](pipe, monkeypatch)
    observed = []
    with pytest.raises(DisplayError, match="sink_exception:RuntimeError") as caught:
        try:
            pipe.output.show(decoded(generation, 2))
        finally:
            observed.append(pipe.host.visible_content)  # state at the instant control returns
    assert observed == [None]
    assert isinstance(caught.value.__cause__, RuntimeError) and str(caught.value.__cause__) == "injected"
    assert caught.value.code == "sink_exception:RuntimeError"
    assert caught.value.cleanup_error is None
    assert pipe.output.rejected[-1] == "sink_exception:RuntimeError"
    monkeypatch.undo()
    assert_sink_closed(pipe, generation)
    assert pipe.host.residual_state == ()


def test_failure_with_no_prior_content_still_deactivates_the_output(make, monkeypatch):
    pipe = make()
    pipe.open_session()
    assert pipe.setup_type111(12).accepted
    generation = pipe.receiver.stream_identity(111).stream_generation
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser())
    with pytest.raises(DisplayError, match="sink_exception:RuntimeError"):
        pipe.output.show(decoded(generation, 1))
    monkeypatch.undo()
    assert_sink_closed(pipe, generation)


def test_frame_error_codes_and_causes_are_preserved(shown, monkeypatch):
    pipe, generation = shown
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser_frame_error("invalid_png"))
    with pytest.raises(DisplayError) as caught:
        pipe.output.show(decoded(generation, 2))
    assert caught.value.code == "invalid_png"
    assert isinstance(caught.value.__cause__, FrameError) and caught.value.__cause__.code == "invalid_png"
    assert pipe.host.visible_content is None


def raiser_frame_error(code):
    def fail(*_args, **_kwargs):
        raise FrameError(code)
    return fail


def test_base_exceptions_are_not_converted(shown, monkeypatch):
    pipe, generation = shown
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser("stop", KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        pipe.output.show(decoded(generation, 2))


# ---- cleanup failure is reported, never hidden, and never replaces the original error ----
def test_revocation_failure_keeps_the_original_error_and_reports_the_cleanup_failure(shown, monkeypatch):
    pipe, generation = shown
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser())
    monkeypatch.setattr(pipe.host, "revoke", raiser("host unavailable", OSError))
    with pytest.raises(DisplayError, match="sink_exception:RuntimeError") as caught:
        pipe.output.show(decoded(generation, 2))
    assert str(caught.value.__cause__) == "injected"
    assert isinstance(caught.value.cleanup_error, OSError) and str(caught.value.cleanup_error) == "host unavailable"
    assert pipe.output.cleanup_failures == ["OSError"]
    assert pipe.host.visible_content is not None  # truthfully NOT withdrawn: the host refused
    monkeypatch.undo()
    with pytest.raises(DisplayError, match="output_inactive"):
        pipe.output.show(decoded(generation, 3))  # the sink still refuses frames
    pipe.output.clear()  # a retry now succeeds and withdraws
    assert pipe.host.visible_content is None


def test_cleanup_failure_on_an_ordinary_rejection_is_reported_too(shown, monkeypatch):
    pipe, generation = shown
    monkeypatch.setattr(pipe.host, "revoke", raiser("host unavailable", OSError))
    with pytest.raises(DisplayError, match="stale_stream_generation") as caught:
        pipe.output.show(decoded(generation + 1, 2))
    assert isinstance(caught.value.cleanup_error, OSError)
    assert pipe.output.cleanup_failures == ["OSError"]


# ---- concurrency: deterministic hand-offs, no sleeps ----
def test_revocation_during_in_flight_conversion_prevents_late_presentation(shown, monkeypatch):
    pipe, generation = shown
    real_convert = type111_ingest.png_to_rgb24
    entered, release = threading.Event(), threading.Event()

    def slow_convert(png):
        entered.set()
        assert release.wait(WAIT_SECONDS)
        return real_convert(png)

    monkeypatch.setattr(type111_ingest, "png_to_rgb24", slow_convert)
    outcome = []

    def worker():
        try:
            pipe.output.show(decoded(generation, 2, (9, 9, 9)))
            outcome.append("presented")
        except DisplayError as exc:
            outcome.append(exc.code)

    thread = threading.Thread(target=worker)
    thread.start()
    assert entered.wait(WAIT_SECONDS)
    pipe.output.fail_closed("revoked while converting")  # takes the same lock: conversion holds none
    assert pipe.host.visible_content is None
    release.set()
    thread.join(WAIT_SECONDS)
    assert not thread.is_alive()
    assert outcome == ["output_inactive"]
    assert pipe.host.visible_content is None and pipe.output.last_bound is None


def test_unexpected_error_after_a_concurrent_revocation_still_reports_one_clean_state(shown, monkeypatch):
    pipe, generation = shown
    entered, release = threading.Event(), threading.Event()

    def failing_slow_convert(_png):
        entered.set()
        assert release.wait(WAIT_SECONDS)
        raise RuntimeError("injected")

    monkeypatch.setattr(type111_ingest, "png_to_rgb24", failing_slow_convert)
    outcome = []

    def worker():
        try:
            pipe.output.show(decoded(generation, 2))
        except DisplayError as exc:
            outcome.append((exc.code, type(exc.__cause__).__name__))

    thread = threading.Thread(target=worker)
    thread.start()
    assert entered.wait(WAIT_SECONDS)
    pipe.output.clear()
    release.set()
    thread.join(WAIT_SECONDS)
    assert outcome == [("sink_exception:RuntimeError", "RuntimeError")]
    assert pipe.host.visible_content is None


def test_repeated_cleanup_after_a_failure_is_safe_and_idempotent(shown, monkeypatch):
    pipe, generation = shown
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser())
    with pytest.raises(DisplayError):
        pipe.output.show(decoded(generation, 2))
    monkeypatch.undo()
    for _ in range(3):
        pipe.output.clear()
        pipe.output.fail_closed("again")
        pipe.output.deactivate()
    pipe.disconnect()
    pipe.disconnect()
    assert pipe.host.visible_content is None and pipe.host.residual_state == ()
    assert pipe.session_residual() == ()


# ---- through the real receiver / dispatcher ----
def test_dispatcher_path_leaves_no_stale_content_after_a_sink_exception(make, stream, monkeypatch):
    pipe = make()
    client = start_type111(pipe)
    client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
    assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
    assert pipe.host.visible_content is not None
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser())
    client.sendall(stream.frame_message(1, timestamp=6))
    outcome = pipe.pump_frame()
    client.close()
    assert not outcome.accepted and outcome.fault is not None
    assert pipe.host.visible_content is None
    assert pipe.output.rejected[-1] == "sink_exception:RuntimeError"
    assert pipe.host.residual_state == ()


# ---- Type110 stays independent of every Type111 sink failure ----
@pytest.mark.parametrize("point", sorted(INJECTIONS))
def test_type110_is_untouched_by_a_type111_sink_exception(make, stream, monkeypatch, point):
    pipe = make()
    client, primary = start_type111(pipe, with_primary=True)
    primary.sendall(stream.primary_message(0))
    pipe.receiver.receive_primary_frame(pipe.generation)
    held, decoder, listener = pipe.primary_display.current, pipe.receiver.primary_decoder, pipe.receiver.primary
    client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
    assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
    INJECTIONS[point](pipe, monkeypatch)
    generation = pipe.receiver.stream_identity(111).stream_generation
    with pytest.raises(DisplayError, match="sink_exception"):
        pipe.output.show(decoded(generation, 9))
    monkeypatch.undo()
    assert pipe.host.visible_content is None
    assert pipe.primary_display.current is held  # Type110 output was never cleared
    assert pipe.receiver.primary is listener and pipe.receiver.primary_decoder is decoder
    # A direct sink call withdraws Display 1 only; the receiver keeps both streams and is not FAILED.
    assert not decoder.closed and pipe.receiver.state is ReceiverState.BOTH_ACTIVE
    primary.sendall(stream.primary_message(1))
    assert pipe.receiver.receive_primary_frame(pipe.generation).startswith(b"\x89PNG")
    client.close()
    primary.close()


# ---- review follow-ups: atomic withdrawal, pending-withdrawal reporting, pipeline-level cleanup failure ----
def test_second_phase_failures_withdraw_while_the_output_lock_is_held(shown, monkeypatch):
    pipe, generation = shown
    owned_during_revoke = []
    real_revoke = pipe.host.revoke

    def spying_revoke(reason):
        owned_during_revoke.append(pipe.output._lock._is_owned())
        return real_revoke(reason)

    monkeypatch.setattr(pipe.host, "revoke", spying_revoke)
    monkeypatch.setattr(pipe.coordinator, "submit_frame", raiser())
    with pytest.raises(DisplayError, match="sink_exception"):
        pipe.output.show(decoded(generation, 2))
    assert owned_during_revoke == [True]  # no window for a re-activation between check and withdrawal


@pytest.mark.parametrize("timestamp, code", [(0, "timestamp_regression")])
def test_timestamp_regression_is_rejected_and_withdrawn(shown, timestamp, code):
    pipe, generation = shown
    with pytest.raises(DisplayError) as caught:
        pipe.output.show(decoded(generation, timestamp))
    assert caught.value.code == code and caught.value.cleanup_error is None
    assert pipe.host.visible_content is None and pipe.output.cleanup_failures == []


def test_missing_lease_is_rejected_and_withdrawn(shown, monkeypatch):
    pipe, generation = shown
    monkeypatch.setattr(type(pipe.coordinator), "lease", property(lambda _self: None))
    with pytest.raises(DisplayError, match="lease_rejected:REJECTED_NO_LEASE"):
        pipe.output.show(decoded(generation, 2))
    monkeypatch.undo()
    assert pipe.host.visible_content is None and pipe.output.cleanup_failures == []


def test_a_reactivated_output_does_not_accept_a_frame_converted_for_the_old_stream(shown, monkeypatch):
    import dataclasses
    pipe, generation = shown
    real_convert = type111_ingest.png_to_rgb24
    entered, release = threading.Event(), threading.Event()

    def slow_convert(png):
        entered.set()
        assert release.wait(WAIT_SECONDS)
        return real_convert(png)

    monkeypatch.setattr(type111_ingest, "png_to_rgb24", slow_convert)
    outcome = []
    thread = threading.Thread(target=lambda: outcome.append(_show_code(pipe, decoded(generation, 2))))
    thread.start()
    assert entered.wait(WAIT_SECONDS)
    pipe.output.fail_closed("old stream ended")
    pipe.output.activate(dataclasses.replace(pipe.receiver.stream_identity(111)))  # a new activation
    release.set()
    thread.join(WAIT_SECONDS)
    assert outcome == ["output_inactive"]
    assert pipe.host.visible_content is None


def _show_code(pipe, frame):
    try:
        pipe.output.show(frame)
        return "presented"
    except DisplayError as exc:
        return exc.code


def test_failed_withdrawal_is_visible_in_residual_until_it_succeeds(shown, monkeypatch):
    pipe, generation = shown
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser())
    monkeypatch.setattr(pipe.host, "revoke", raiser("host unavailable", OSError))
    with pytest.raises(DisplayError):
        pipe.output.show(decoded(generation, 2))
    assert pipe.output.withdrawal_pending and "withdrawal_pending" in pipe.residual()
    monkeypatch.undo()
    pipe.output.clear()
    assert not pipe.output.withdrawal_pending and "withdrawal_pending" not in pipe.residual()


def test_pipeline_records_a_failed_withdrawal_instead_of_losing_it(make, stream, monkeypatch):
    pipe = make()
    client = start_type111(pipe)
    client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
    assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
    monkeypatch.setattr(type111_ingest, "png_to_rgb24", raiser())
    real_revoke = pipe.host.revoke

    def sink_only_failure(reason):
        if pipe.output._lock._is_owned():  # only the sink's own withdrawals hold its lock
            raise OSError("host unavailable")
        return real_revoke(reason)

    monkeypatch.setattr(pipe.host, "revoke", sink_only_failure)
    client.sendall(stream.frame_message(1, timestamp=6))
    outcome = pipe.pump_frame()  # must not raise
    client.close()
    assert not outcome.accepted
    assert pipe.output.cleanup_failures and pipe.cleanup_failures
    assert pipe.faults and pipe.faults[-1].cleanup_ok is False
    assert pipe.output.withdrawal_pending and "withdrawal_pending" in pipe.residual()
    assert pipe.host.visible_content is None  # the coordinator's own revoke still withdrew it
    monkeypatch.undo()
    pipe.output.clear()  # once the sink's path works again the pending flag clears
    assert not pipe.output.withdrawal_pending
