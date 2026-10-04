"""R5Y lifecycle, transaction, media and ownership checks with invented values."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-sandbox"))

from r5y_receiver_core import (  # noqa: E402
    CleanupManager, FailurePoint, FaultInjector, LEGAL_TRANSITIONS, ListenerHandle,
    MediaFrame, MockDisplay1Sink, MockSecurityProvider, PrimaryStreamState,
    ReceiverCore, ReceiverError, ReceiverSession, ReceiverState, SessionGeneration,
    SetupRequest, SetupResponse, SetupTransaction, StreamDescriptor, serialize_setup,
)


def created(generation=1, *, core=None, faults=None):
    core = core or ReceiverCore()
    key = SessionGeneration(generation)
    session = core.create_session(f"session-{generation:03d}", key, faults=faults)
    return core, key, session


def setup(core, key, *, secondary=True, enabled=True, faults=None):
    session = core.sessions[key]
    request = SetupRequest(session.session_id, key, session.primary.descriptor,
                           request_secondary=secondary, enable_secondary=enabled)
    return core.setup(request, faults=faults)


def ready(*, secondary=True):
    core, key, _ = created()
    session = setup(core, key, secondary=secondary)
    return core, key, session


def assert_closed(core, key):
    result = core.teardown(key)
    assert core.sessions[key].state is ReceiverState.CLOSED
    assert core.resource_snapshot().sessions == 0
    assert core.resource_snapshot().secondary_total == 0
    assert core.primary_intact(key)
    return result


def test_primary_only_lifecycle():
    core, key, session = ready(secondary=False)
    assert session.state is ReceiverState.PRIMARY_READY
    assert len(session.response.streams) == 1
    assert core.resource_snapshot().secondary_total == 0
    core.start_streaming(key)
    assert session.state is ReceiverState.STREAMING
    assert_closed(core, key)


def test_secondary_lifecycle_and_generation_ownership():
    core, key, session = ready()
    assert session.state is ReceiverState.SECONDARY_READY
    assert session.secondary.generation == key
    assert len(session.response.streams) == 2
    assert core.resource_snapshot().secondary_total == 5
    assert core.primary_intact(key)
    core.start_streaming(key)
    assert core.send_frame(MediaFrame(key, 1, "frame-001"))
    assert_closed(core, key)


def test_type111_disabled_has_no_child():
    core, key, session = ready(secondary=False)
    assert session.secondary is None
    assert core.cleanup_manager.owned(key) is None
    assert_closed(core, key)


@pytest.mark.parametrize("bad", [0, -1, True, "1"])
def test_generation_validation(bad):
    with pytest.raises(ReceiverError, match="invalid_generation"):
        SessionGeneration(bad)


@pytest.mark.parametrize("fault", [
    FailurePoint.SETUP_VALIDATION, FailurePoint.SECONDARY_RESPONSE_CREATION,
    FailurePoint.LISTENER_ALLOCATION, FailurePoint.SECURITY_INITIALIZATION,
    FailurePoint.DECODER_INITIALIZATION, FailurePoint.DISPLAY_INITIALIZATION,
    FailurePoint.SETUP_COMMIT,
])
def test_setup_faults_rollback_child_and_preserve_primary(fault):
    core, key, _ = created()
    session = setup(core, key, faults=FaultInjector(fault))
    assert session.state is ReceiverState.PRIMARY_READY
    assert session.secondary is None
    assert len(session.response.streams) == 1
    assert core.resource_snapshot().secondary_total == 0
    assert core.primary_intact(key)
    core.start_streaming(key)
    assert_closed(core, key)


def test_session_creation_fault_has_no_resources():
    core = ReceiverCore()
    with pytest.raises(ReceiverError, match="injected_session_creation"):
        created(core=core, faults=FaultInjector(FailurePoint.SESSION_CREATION))
    assert core.resource_snapshot().sessions == 0
    assert core.resource_snapshot().secondary_total == 0


def test_setup_request_requires_explicit_enable_flag():
    core, key, session = created()
    with pytest.raises(ReceiverError, match="secondary_requires_explicit_flag"):
        SetupRequest(session.session_id, key, session.primary.descriptor, True, False)
    assert session.state is ReceiverState.SESSION_CREATED
    assert core.resource_snapshot().secondary_total == 0


def test_setup_session_mismatch_rolls_back():
    core, key, session = created()
    wrong = SetupRequest("session-wrong", key, session.primary.descriptor, True, True)
    assert core.setup(wrong).last_secondary_error == "setup_session_or_primary_mismatch"
    assert core.primary_intact(key)
    assert core.resource_snapshot().secondary_total == 0


def test_all_state_transitions_match_formal_table():
    core, key, session = created()
    for origin in ReceiverState:
        for target in ReceiverState:
            session.state = origin
            if target in LEGAL_TRANSITIONS[origin]:
                session.transition(target)
                assert session.state is target
            else:
                with pytest.raises(ReceiverError, match="illegal_state_transition"):
                    session.transition(target)
                assert session.state is origin


def test_setup_transaction_abort_is_idempotent():
    response = SetupResponse((StreamDescriptor(110, "synthetic-a"),))
    txn = SetupTransaction(SessionGeneration(1), response)
    assert txn.abort() is response
    assert txn.abort() is response
    assert txn.candidate is None


def test_setup_transaction_commit_is_immutable_and_final():
    descriptor = StreamDescriptor(110, "synthetic-a")
    response = SetupResponse((descriptor,))
    txn = SetupTransaction(SessionGeneration(1), response)
    candidate = SetupResponse((descriptor, StreamDescriptor(111, "synthetic-b", "mock-port-50001")))
    txn.set_candidate(candidate)
    assert txn.commit() is candidate
    with pytest.raises(ReceiverError):
        txn.abort()
    with pytest.raises(ReceiverError):
        txn.set_candidate(response)
    with pytest.raises(ReceiverError):
        txn.commit()


def test_setup_transaction_rejects_primary_replacement():
    original = SetupResponse((StreamDescriptor(110, "synthetic-a"),))
    txn = SetupTransaction(SessionGeneration(1), original)
    with pytest.raises(ReceiverError, match="invalid_transaction_candidate"):
        txn.set_candidate(SetupResponse((StreamDescriptor(110, "synthetic-a"),)))


def test_mock_listener_close_idempotent_and_not_reusable():
    key = SessionGeneration(1)
    listener = ListenerHandle(key, "mock-port-50001")
    listener.accept(key)
    assert listener.accepted
    assert listener.close(key)
    assert not listener.close(key)
    with pytest.raises(ReceiverError):
        listener.accept(key)


def test_mock_listener_rejects_stale_generation():
    key = SessionGeneration(2)
    listener = ListenerHandle(key, "mock-port-50002")
    with pytest.raises(ReceiverError):
        listener.accept(SessionGeneration(1))
    with pytest.raises(ReceiverError):
        listener.close(SessionGeneration(1))
    assert not listener.closed


def test_mock_security_has_only_symbolic_state():
    key = SessionGeneration(1)
    context = MockSecurityProvider().create(key)
    assert context.context_label == "mock-security-1"
    assert not context.ready
    context.initialize()
    assert context.unwrap_symbol(MediaFrame(key, 1, "frame-001")) == "clear-frame-001"
    assert context.destroy()
    assert not context.destroy()
    with pytest.raises(ReceiverError):
        context.initialize()


def test_ordered_symbolic_media_to_mock_display():
    core, key, _ = ready()
    core.start_streaming(key)
    child = core.cleanup_manager.owned(key)
    for sequence in range(1, 4):
        assert core.send_frame(MediaFrame(key, sequence, f"frame-{sequence:03d}"))
    assert child.display.frame_count == 3
    assert child.display.current.symbol == "decoded-clear-frame-003"
    assert child.stream.last_sequence == 3
    assert_closed(core, key)


@pytest.mark.parametrize("sequence", [0, -1, True, "1"])
def test_invalid_media_sequence_rejected(sequence):
    with pytest.raises(ReceiverError, match="invalid_frame_sequence"):
        MediaFrame(SessionGeneration(1), sequence, "frame-001")


@pytest.mark.parametrize("sequence", [1, 3, 100])
def test_out_of_order_or_replayed_frame_clears_display(sequence):
    core, key, _ = ready()
    core.start_streaming(key)
    assert core.send_frame(MediaFrame(key, 1, "frame-001"))
    assert not core.send_frame(MediaFrame(key, sequence, "frame-stale"))
    child = core.cleanup_manager.owned(key)
    assert child.display.current is None
    assert child.display.clear_reason == "stale"
    assert child.stream.last_sequence == 1
    assert_closed(core, key)


@pytest.mark.parametrize("other", [2, 3, 99])
def test_old_or_future_generation_frame_cannot_reach_current_sink(other):
    core, key, _ = ready()
    core.start_streaming(key)
    child = core.cleanup_manager.owned(key)
    assert not core.send_frame(MediaFrame(SessionGeneration(other), 1, "frame-001"))
    assert child.display.current is None
    assert child.display.frame_count == 0
    assert_closed(core, key)


@pytest.mark.parametrize("fault,sequence", [
    (FailurePoint.FIRST_FRAME, 1), (FailurePoint.MID_STREAM_FRAME, 2),
    (FailurePoint.DECODER_PROCESSING, 1), (FailurePoint.DISPLAY_UPDATE, 1),
])
def test_media_fault_contains_secondary_and_preserves_primary(fault, sequence):
    core, key, session = ready()
    core.start_streaming(key)
    if sequence == 2:
        assert core.send_frame(MediaFrame(key, 1, "frame-001"))
    assert not core.send_frame(MediaFrame(key, sequence, f"frame-{sequence:03d}"), faults=FaultInjector(fault))
    assert session.state is ReceiverState.PRIMARY_READY
    assert session.secondary is None
    assert core.resource_snapshot().secondary_total == 0
    assert core.primary_intact(key)
    assert_closed(core, key)


@pytest.mark.parametrize("reason", ["lost", "reroute", "stale", "session_death"])
def test_display_fail_clear_reasons(reason):
    core, key, _ = ready()
    core.start_streaming(key)
    assert core.send_frame(MediaFrame(key, 1, "frame-001"))
    child = core.cleanup_manager.owned(key)
    core.clear_display(key, reason)
    assert child.display.current is None
    assert child.display.clear_reason == reason
    assert_closed(core, key)


def test_teardown_is_idempotent_and_cleans_every_resource():
    core, key, _ = ready()
    child = core.cleanup_manager.owned(key)
    result = assert_closed(core, key)
    assert result.performed and not result.errors
    assert child.listener.closed and child.security.destroyed and child.decoder.closed
    assert child.display.closed and not child.stream.active
    assert not core.teardown(key).performed


def test_injected_teardown_error_still_cleans_child():
    core, key, session = ready()
    result = core.teardown(key, faults=FaultInjector(FailurePoint.TEARDOWN))
    assert result.errors == ("injected_teardown",)
    assert core.resource_snapshot().secondary_total == 0
    assert core.primary_intact(key)


def test_duplicate_teardown_fault_remains_noop():
    core, key, _ = ready()
    assert_closed(core, key)
    assert not core.teardown(key, faults=FaultInjector(FailurePoint.DUPLICATE_TEARDOWN)).performed
    assert core.resource_snapshot().secondary_total == 0


def test_cleanup_partial_initialization_is_safe():
    manager = CleanupManager()
    key = SessionGeneration(1)
    child = manager.reserve(key)
    child.listener = ListenerHandle(key, "mock-port-50001")
    assert manager.cleanup(key).performed
    assert child.listener.closed
    assert not manager.cleanup(key).performed
    assert manager.counts() == (0, 0, 0, 0, 0, 0)


def test_real_mock_close_exception_remains_accounted_until_retry():
    class FlakyListener(ListenerHandle):
        attempts = 0
        def close(self, generation):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("temporary model failure")
            return super().close(generation)

    class FlakyProvider:
        def allocate(self, generation):
            return FlakyListener(generation, "mock-port-50001")

    core = ReceiverCore(listener_provider=FlakyProvider())
    _, key, _ = created(core=core)
    setup(core, key)
    result = core.teardown(key)
    assert result.errors == ("listener_close_RuntimeError",)
    assert core.resource_snapshot().unresolved_bundles == 1
    assert core.resource_snapshot().listeners == 1
    retried = core.teardown(key)
    assert retried.performed and not retried.errors
    assert core.resource_snapshot().secondary_total == 0


def test_reconnect_old_handles_do_not_affect_new_generation():
    core, first, _ = ready()
    old_child = core.cleanup_manager.owned(first)
    core.start_streaming(first)
    core.send_frame(MediaFrame(first, 1, "frame-001"))
    second = SessionGeneration(2)
    core.create_session("session-002", second)
    setup(core, second)
    core.start_streaming(second)
    new_child = core.cleanup_manager.owned(second)
    assert old_child.listener.closed and old_child.security.destroyed
    assert not core.send_frame(MediaFrame(first, 2, "frame-old"))
    with pytest.raises(ReceiverError):
        new_child.listener.close(first)
    assert not core.teardown(first).performed
    assert core.cleanup_manager.owned(second) is new_child
    assert new_child.listener is not old_child.listener
    assert new_child.security is not old_child.security
    assert_closed(core, second)


def test_rapid_reconnect_three_generations():
    core = ReceiverCore()
    for value in (1, 2, 3):
        _, key, _ = created(value, core=core)
        setup(core, key)
        core.start_streaming(key)
        assert core.send_frame(MediaFrame(key, 1, f"frame-{value:03d}"))
    assert core.sessions[SessionGeneration(1)].state is ReceiverState.CLOSED
    assert core.sessions[SessionGeneration(2)].state is ReceiverState.CLOSED
    assert_closed(core, SessionGeneration(3))


def test_hundred_cycle_lifecycle_leak_accounting():
    core = ReceiverCore()
    for value in range(1, 101):
        _, key, _ = created(value, core=core)
        setup(core, key)
        core.start_streaming(key)
        assert core.send_frame(MediaFrame(key, 1, f"frame-{value:03d}"))
        assert_closed(core, key)
    assert len(core.sessions) == 100


def test_canonical_serializer_is_deterministic_and_not_wire_format():
    response = SetupResponse((StreamDescriptor(110, "synthetic-a"),))
    first = serialize_setup(response)
    assert first == serialize_setup(response)
    assert b"SYNTHETIC_MODEL_SERIALIZER" in first
    assert b"NOT_CARPLAY_WIRE_FORMAT" in first


def test_event_trace_is_ordered_and_secret_free():
    core, key, _ = ready()
    core.start_streaming(key)
    core.send_frame(MediaFrame(key, 1, "frame-001"))
    assert_closed(core, key)
    assert [event.index for event in core.events] == list(range(1, len(core.events) + 1))
    assert core.events[0].kind == "SESSION_CREATED"
    assert core.events[-1].kind == "GENERATION_CLOSED"
    assert not any("key" in event.detail.lower() for event in core.events)


def test_mock_adapter_exception_rolls_back_partial_setup():
    class BrokenSecurityProvider:
        def create(self, generation):
            raise RuntimeError("private diagnostic")

    core = ReceiverCore(security_provider=BrokenSecurityProvider())
    _, key, _ = created(core=core)
    session = setup(core, key)
    assert session.last_secondary_error == "adapter_RuntimeError"
    assert "private diagnostic" not in repr(core.events)
    assert core.resource_snapshot().secondary_total == 0
    assert core.primary_intact(key)
