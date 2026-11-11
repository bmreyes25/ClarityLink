"""Synthetic-only project child ownership and response delivery failures."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from response_delivery_model import DeliveryState, SyntheticResponseDelivery


def stock_snapshot(model):
    return (model.type110_active, model.type110_crypto,
            model.center_screen_state, model.audio_active)


def assert_project_did_not_mutate_stock(model):
    assert model.project_stock_mutations == 0


def ready_child():
    model = SyntheticResponseDelivery()
    model.allocate()
    model.listener_created()
    model.append_succeeded()
    model.release_entry_local()
    model.accept_socket()
    return model


def prepared_child():
    model = SyntheticResponseDelivery()
    model.allocate()
    model.listener_created()
    model.append_succeeded()
    return model


def test_serialized_history_survives_cleanup_and_transport_outcomes():
    model = prepared_child()
    model.serialization_succeeded(b"synthetic-plist-type110-and-111")
    payload = model.serialized_bytes
    assert model.delivery_state is DeliveryState.SERIALIZED_LOCAL
    model.project_failure("cleanup-after-serialization")
    assert model.serialized_bytes == payload
    assert model.delivery_state is DeliveryState.SERIALIZED_LOCAL
    assert model.close_count == model.decoder_release_count == 1
    assert model.type110_active and model.audio_active

    model.transmission_started()
    model.transmission_failed(bytes_written=7)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.known_output_bytes == 7
    model.project_failure("cleanup-after-uncertain-send")
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.serialized_bytes == payload and model.type110_active
    assert model.close_count == model.decoder_release_count == 1


def test_serialization_failure_and_transport_completion_are_distinct():
    failed = prepared_child()
    failed.serialization_failed()
    assert failed.delivery_state is DeliveryState.SERIALIZATION_FAILED
    assert failed.serialized_bytes is None
    assert not failed.response_graph_live and not failed.entry_array_owned
    assert failed.graph_release_count == 1
    assert failed.close_count == failed.decoder_release_count == 1

    no_output = prepared_child()
    no_output.serialization_succeeded(b"wire")
    no_output.transmission_started()
    no_output.transmission_failed(bytes_written=0)
    assert no_output.delivery_state is DeliveryState.SEND_FAILED_NO_OUTPUT
    assert no_output.serialized_bytes == b"wire"

    complete = prepared_child()
    complete.serialization_succeeded(b"complete-synthetic-plist")
    complete.transmission_started()
    complete.transport_completed()
    assert complete.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    assert complete.known_output_bytes == len(complete.serialized_bytes)
    assert complete.peer_acceptance == "UNKNOWN"


def test_uncertain_partial_write_can_later_complete_locally_without_peer_ack():
    model = prepared_child()
    model.serialization_succeeded(b"synthetic-wire")
    model.retryable_write("partial-write", bytes_written=3)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.known_output_bytes == 3
    model.transport_completed()
    assert model.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    assert model.peer_acceptance == "UNKNOWN"


def test_terminal_zero_progress_after_partial_write_retains_uncertain_delivery():
    model = prepared_child()
    model.serialization_succeeded(b"synthetic-wire")
    model.retryable_write("partial-write", bytes_written=3)
    model.transmission_failed(bytes_written=0)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_offset == model.known_output_bytes == 3
    assert "transmission-failed-delivery-unknown" in model.events
    assert "transmission-failed-no-output" not in model.events


def test_repeated_transmission_start_cannot_reset_partial_delivery_history():
    model = prepared_child()
    model.serialization_succeeded(b"synthetic-wire")
    model.retryable_write("partial-write", bytes_written=3)
    with pytest.raises(RuntimeError, match="cannot transmit before local serialization"):
        model.transmission_started()
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_offset == model.known_output_bytes == 3


def test_serialization_failure_cannot_overwrite_serialized_delivery_history():
    model = prepared_child()
    model.serialization_succeeded(b"synthetic-wire")
    model.retryable_write("partial-write", bytes_written=3)
    before = (model.delivery_state, model.serialized_bytes, model.transmission_offset,
              model.known_output_bytes, model.close_count, model.decoder_release_count)
    with pytest.raises(RuntimeError, match="serialization failure requires a prepared response"):
        model.serialization_failed()
    assert (model.delivery_state, model.serialized_bytes, model.transmission_offset,
            model.known_output_bytes, model.close_count, model.decoder_release_count) == before


@pytest.mark.parametrize("terminal", [False, True])
def test_write_progress_cannot_exceed_serialized_payload_length(terminal):
    model = prepared_child()
    payload = b"wire"
    model.serialization_succeeded(payload)
    model.retryable_write("partial-write", bytes_written=3)
    before = (model.delivery_state, model.transmission_offset, model.known_output_bytes)
    with pytest.raises(ValueError, match="known output exceeds serialized payload length"):
        if terminal:
            model.transmission_failed(bytes_written=2)
        else:
            model.retryable_write("over-reported-write", bytes_written=2)
    assert (model.delivery_state, model.transmission_offset, model.known_output_bytes) == before


def test_invalid_first_write_count_does_not_start_transmission_or_record_progress():
    model = prepared_child()
    model.serialization_succeeded(b"wire")
    before_events = list(model.events)
    with pytest.raises(ValueError, match="known output exceeds serialized payload length"):
        model.retryable_write("invalid-first-write", bytes_written=5)
    assert model.delivery_state is DeliveryState.SERIALIZED_LOCAL
    assert model.transmission_offset == 0 and model.known_output_bytes is None
    assert model.events == before_events


def test_pre_serialization_failure_marks_no_serialized_response_and_is_idempotent():
    model = prepared_child()
    before = stock_snapshot(model)
    model.project_failure("listener-or-authorization-failure")
    assert model.delivery_state is DeliveryState.FAILED_BEFORE_SERIALIZATION
    assert model.serialized_bytes is None
    counts = (model.close_count, model.socket_close_count, model.decoder_release_count)
    model.project_failure("repeat-cleanup")
    assert (model.close_count, model.socket_close_count, model.decoder_release_count) == counts
    assert stock_snapshot(model) == before


def test_project_allocation_and_listener_creation_failures_are_local():
    model = SyntheticResponseDelivery()
    before = stock_snapshot(model)
    model.project_failure("project-allocation-failure")
    assert not model.entry_local and model.close_count == 0
    assert stock_snapshot(model) == before
    model = SyntheticResponseDelivery()
    model.allocate()
    before = stock_snapshot(model)
    model.project_failure("listener-creation-failure")
    assert model.decoder_release_count == 1 and model.close_count == 0
    assert stock_snapshot(model) == before
    assert_project_did_not_mutate_stock(model)


def test_project_response_insertion_failure_rolls_back_only_child():
    model = ready_child()
    before = stock_snapshot(model)
    model.project_failure("response-insertion-failure")
    assert model.close_count == model.socket_close_count == model.decoder_release_count == 1
    assert not model.response_graph_live and stock_snapshot(model) == before
    assert_project_did_not_mutate_stock(model)


def test_serialization_and_http_commit_scheduling_failures_cleanup_child():
    for phase in ("serialization-failure", "http-commit-failure", "state-machine-scheduling-failure"):
        model = ready_child()
        if phase == "serialization-failure":
            model.serialization_failed()
        else:
            model.serialization_succeeded(b"synthetic-wire")
        before = stock_snapshot(model)
        model.project_failure(phase)
        assert model.delivery_state is (
            DeliveryState.SERIALIZATION_FAILED if phase == "serialization-failure"
            else DeliveryState.SERIALIZED_LOCAL
        )
        assert not model.response_graph_live
        assert model.close_count == model.socket_close_count == model.decoder_release_count == 1
        assert stock_snapshot(model) == before
        assert_project_did_not_mutate_stock(model)


def test_partial_and_retryable_writes_remain_pending():
    for phase in ("partial-write", "retryable-eagain"):
        model = ready_child()
        model.serialization_succeeded(b"synthetic-wire")
        before = stock_snapshot(model)
        model.retryable_write(phase, bytes_written=2 if phase == "partial-write" else 0)
        assert model.listener_open and model.accepted_socket_open and model.decoder_live
        assert model.delivery_state is (DeliveryState.DELIVERY_UNKNOWN if phase == "partial-write"
                                        else DeliveryState.TRANSMISSION_STARTED)
        assert model.transmission_offset == (2 if phase == "partial-write" else 0)
        assert stock_snapshot(model) == before
        assert_project_did_not_mutate_stock(model)


def test_consecutive_eagain_then_progress_and_completion_preserves_offset():
    model = ready_child()
    payload = b"abcdef"
    model.serialization_succeeded(payload)
    model.retryable_write("eagain-1", bytes_written=0)
    model.retryable_write("eagain-2", bytes_written=0)
    assert model.delivery_state is DeliveryState.TRANSMISSION_STARTED
    assert model.serialized_bytes == payload and model.transmission_offset == 0
    model.retryable_write("write-prefix", bytes_written=2)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_offset == 2 and model.serialized_bytes == payload
    model.retryable_write("write-suffix", bytes_written=4)
    assert model.transmission_offset == len(payload)
    model.transport_completed()
    assert model.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    assert model.peer_acceptance == "UNKNOWN"


def test_cleanup_during_retry_preserves_delivery_history_and_stock():
    model = ready_child()
    model.serialization_succeeded(b"pending-wire")
    model.retryable_write("eagain", bytes_written=0)
    before = stock_snapshot(model)
    model.project_failure("cancel-pending-send")
    counts = (model.close_count, model.socket_close_count, model.decoder_release_count)
    model.project_failure("repeat-cancel")
    assert model.delivery_state is DeliveryState.TRANSMISSION_STARTED
    assert model.serialized_bytes == b"pending-wire"
    assert (model.close_count, model.socket_close_count, model.decoder_release_count) == counts
    assert stock_snapshot(model) == before


def test_stale_generation_cleanup_cannot_close_current_type111_resources():
    model = ready_child()
    model.generation = 9
    before = (model.listener_open, model.accepted_socket_open, model.decoder_live,
              model.close_count, model.socket_close_count, model.decoder_release_count)
    model.project_failure("late-generation-cleanup", generation=8)
    assert (model.listener_open, model.accepted_socket_open, model.decoder_live,
            model.close_count, model.socket_close_count, model.decoder_release_count) == before
    assert model.type110_active and model.audio_active


def test_terminal_write_error_or_peer_disconnect_waits_for_parent_teardown_event():
    for phase in ("terminal-write-error", "peer-disconnect"):
        model = ready_child()
        model.serialization_succeeded(b"synthetic-wire")
        before = stock_snapshot(model)
        model.retryable_write(phase)  # delivery failure and session teardown are separate events
        assert model.listener_open and model.type110_active and model.audio_active
        assert stock_snapshot(model) == before


def test_connection_finalize_then_parent_teardown_cleans_child_once():
    model = ready_child()
    model.serialization_succeeded(b"synthetic-wire")
    model.parent_connection_finalized()
    after_first = (model.close_count, model.socket_close_count,
                   model.decoder_release_count, model.parent_teardown_count)
    model.honda_parent_teardown()
    assert (model.close_count, model.socket_close_count,
            model.decoder_release_count, model.parent_teardown_count) == (
                after_first[0], after_first[1], after_first[2], after_first[3] + 1)
    assert not model.type110_active and not model.audio_active
    assert model.center_screen_state == "honda-parent-torn-down"
    assert_project_did_not_mutate_stock(model)


def test_repeated_teardown_and_already_stopped_child_are_idempotent():
    model = ready_child()
    model.project_failure("project-only-stop")
    counts = (model.close_count, model.socket_close_count, model.decoder_release_count)
    model.honda_parent_teardown()
    model.honda_parent_teardown()
    assert (model.close_count, model.socket_close_count, model.decoder_release_count) == counts
    assert model.parent_teardown_count == 2
    assert_project_did_not_mutate_stock(model)


def test_project_only_failure_preserves_type110_crypto_screen_and_audio():
    model = ready_child()
    before = stock_snapshot(model)
    model.project_failure("project-only-runtime-failure")
    assert stock_snapshot(model) == before
    assert_project_did_not_mutate_stock(model)


def test_honda_parent_teardown_is_the_only_modeled_stock_state_transition():
    model = ready_child()
    before = stock_snapshot(model)
    model.project_failure("project-only-stop")
    assert stock_snapshot(model) == before
    model.honda_parent_teardown()
    assert model.type110_active is False and model.audio_active is False
    assert model.center_screen_state == "honda-parent-torn-down"
    assert model.type110_crypto == before[1]
    assert model.events.count("honda-parent-session-teardown") == 1
