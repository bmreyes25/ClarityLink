"""CL-T111-INGEST-OWNERSHIP-01: control-plane serialization of the Type111 ingest pipeline.

Evidence scope: SYNTHETIC offline lifecycle only (locally generated clear lab input from
`t111_synth`). NOT iPhone-origin video, NOT Honda integration, NOT a vehicle or CAN operation.
`safeForHonda() == false` and VEHICLE_DEPLOYMENT_NOT_AUTHORIZED are unchanged.

A barrier pauses ``pump_frame`` inside the real receiver while ``disconnect`` starts on another
thread. Host withdrawal must begin before the control-lock wait (the existing simulated
Display 1 frame is gone while pump_frame is still paused), but receiver teardown must not run
until the in-flight control operation returns. Timed waits are bounded: a negative probe that
disconnect has NOT finished, and a poll for the preemptive withdrawal.
"""
import time
import threading

import pytest

import t111_synth as synth
from failsafe_coordinator import Fault
from type111_ingest import Type111IngestPipeline

WAIT_SECONDS = 10.0  # upper bound so a failure can never strand a worker
BLOCKED_PROBE_SECONDS = 0.5  # negative check: disconnect must still be waiting after this
POLL_SECONDS = 0.01


def wait_until(predicate, timeout=WAIT_SECONDS):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(POLL_SECONDS)
    return predicate()


class Race:
    """Pauses the receiver's display fault point once, and records teardown calls by thread."""

    def __init__(self, pipe):
        self.paused = threading.Event()
        self.release = threading.Event()
        self.armed = False
        self.events = []  # (thread name, operation), appended in real execution order
        receiver, original_check = pipe.receiver, pipe.receiver.faults.check

        def check(point):
            if point == "display" and self.armed:
                self.armed = False
                self.paused.set()
                self.release.wait(WAIT_SECONDS)
            return original_check(point)

        receiver.faults.check = check
        for name in ("teardown", "teardown_secondary"):
            setattr(receiver, name, self._recorded(name, getattr(receiver, name)))

    def _recorded(self, name, original):
        def call(*args, **kwargs):
            self.events.append((threading.current_thread().name, name))
            return original(*args, **kwargs)
        return call


@pytest.fixture
def pipeline():
    pipe = Type111IngestPipeline(lab_mode=True, clock=synth.Clock(), receiver_kwargs=dict(synth.DIMENSIONS))
    yield pipe
    pipe.receiver.teardown(pipe.generation)


@pytest.mark.parametrize("kind, full_teardown", [
    (Fault.CARPLAY_ENDED, True),                 # whole receiver session goes
    (Fault.TYPE111_TRANSPORT_FAILURE, False),    # only the secondary stream goes
])
def test_disconnect_waits_for_in_flight_pump_frame_then_withdraws_everything(pipeline, kind, full_teardown):
    stream = synth.SyntheticStream(4)
    secondary, primary = synth.start_type111(pipeline, with_primary=True)
    race = Race(pipeline)
    outcomes, reports = {}, {}

    def pump():
        outcomes["pump"] = pipeline.pump_frame()
        race.events.append(("pump", "returned"))

    def disconnect():
        reports["disconnect"] = pipeline.disconnect(kind)
        race.events.append(("disconnect", "returned"))

    pump_thread = threading.Thread(target=pump, name="pump")
    disconnect_thread = threading.Thread(target=disconnect, name="disconnect")
    try:
        secondary.sendall(stream.config_message())
        secondary.sendall(stream.frame_message(0))
        assert pipeline.pump_frame().accepted and pipeline.pump_frame().accepted
        assert pipeline.host.visible_content is not None  # Display 1 content is live
        primary_listener = pipeline.receiver.primary
        assert primary_listener is not None

        race.armed = True
        secondary.sendall(stream.frame_message(1))
        pump_thread.start()
        assert race.paused.wait(WAIT_SECONDS), "pump_frame never reached the receiver pause point"
        disconnect_thread.start()

        # Serialization: teardown cannot interleave while pump_frame is in flight.
        # Preemptive withdrawal: the live Display 1 frame is withdrawn while pump_frame is paused.
        assert wait_until(lambda: pipeline.host.visible_content is None), \
            "Display 1 content was not withdrawn before the control-lock wait"
        disconnect_thread.join(BLOCKED_PROBE_SECONDS)
        assert disconnect_thread.is_alive(), "disconnect ran while pump_frame was still in flight"
        assert pipeline.host.visible_content is None and not pipeline.host.lease_held
        assert not race.events, race.events
        assert pipeline.receiver.snapshot().sessions == 1 and pipeline.receiver.secondary is not None
        assert pipeline.receiver.primary is primary_listener  # Type110 untouched meanwhile
    finally:
        race.release.set()
        for thread in (pump_thread, disconnect_thread):
            if thread.ident is not None:
                thread.join(WAIT_SECONDS)
        secondary.close()
        primary.close()
    assert not pump_thread.is_alive() and not disconnect_thread.is_alive()

    # Nothing tore down before release (asserted while paused). Afterwards the in-flight pump finds its
    # output withdrawn and fails closed on its own thread; the disconnect teardown runs only after the
    # pump has returned and released the control lock.
    events = race.events
    pump_returned = events.index(("pump", "returned"))
    assert all(who == "pump" for who, _ in events[:pump_returned]), events
    assert any(who == "disconnect" and op.startswith("teardown") for who, op in events), events
    assert all(who == "disconnect" for who, _ in events[pump_returned + 1:]), events
    assert not outcomes["pump"].accepted  # the paused frame was withdrawn, not presented
    assert not reports["disconnect"].failed

    # Postconditions: Display 1 lease/content withdrawn, Type111 resources released.
    assert pipeline.host.visible_content is None and pipeline.host.residual_state == ()
    assert not pipeline.host.lease_held and pipeline.coordinator.lease is None
    assert pipeline.residual() == ()
    snapshot = pipeline.receiver.snapshot()
    receiver = pipeline.receiver
    assert receiver.secondary is None and receiver.decoder is None and receiver.security is None
    assert (snapshot.secondary_listeners, snapshot.displayed_frames, snapshot.display_uncleared) == (0, 0, 0)
    if full_teardown:
        assert pipeline.session_residual() == ()
        assert snapshot.sessions == 0 and snapshot.primary_listeners == 0
    else:  # the separately active Type110 primary stream stays independent and up
        assert snapshot.sessions == 1 and snapshot.primary_listeners == 1
        assert pipeline.receiver.primary is primary_listener


def test_failed_preemptive_withdrawal_is_retried_in_serialized_cleanup(pipeline, monkeypatch):
    """A raising preemptive withdrawal is recorded, then retried; receiver cleanup still runs."""
    stream = synth.SyntheticStream(4)
    secondary, primary = synth.start_type111(pipeline, with_primary=True)
    secondary.sendall(stream.config_message())
    secondary.sendall(stream.frame_message(0))
    try:
        assert pipeline.pump_frame().accepted and pipeline.pump_frame().accepted
        assert pipeline.host.visible_content is not None
        original, calls = pipeline.output.fail_closed, []

        def flaky(reason):
            calls.append(threading.current_thread().name)
            if len(calls) == 1:  # only the preemptive attempt fails
                raise RuntimeError("synthetic_withdrawal_failure")
            return original(reason)

        monkeypatch.setattr(pipeline.output, "fail_closed", flaky)
        report = pipeline.disconnect(Fault.CARPLAY_ENDED)
    finally:
        secondary.close()
        primary.close()
    assert len(calls) == 2, calls  # preemptive attempt + serialized retry
    assert "RuntimeError" in pipeline.cleanup_failures
    assert not report.failed  # the retry succeeded, so cleanup is complete
    assert pipeline.host.visible_content is None and pipeline.residual() == ()
    assert pipeline.session_residual() == ()


def test_withdrawal_failing_twice_is_reported_without_skipping_receiver_cleanup(pipeline, monkeypatch):
    secondary, primary = synth.start_type111(pipeline, with_primary=True)
    try:
        def broken(reason):
            raise RuntimeError("synthetic_withdrawal_failure")

        monkeypatch.setattr(pipeline.output, "fail_closed", broken)
        report = pipeline.disconnect(Fault.CARPLAY_ENDED)  # must not raise before cleanup
    finally:
        secondary.close()
        primary.close()
    assert "withdrawal" in report.failed
    assert pipeline.session_residual() == ()  # receiver teardown still ran
    assert pipeline.faults[-1].cleanup_ok is False
