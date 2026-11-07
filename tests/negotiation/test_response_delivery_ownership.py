"""Synthetic-only project child ownership and response delivery failures."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from response_delivery_model import DeliveryState, SyntheticResponseDelivery


def _generation(model, generation=None):
    return model.generation if generation is None else generation


def serialize(model, payload, *, generation=None):
    model.serialization_succeeded(payload, generation=_generation(model, generation))


def fail_serialization(model, *, generation=None):
    model.serialization_failed(generation=_generation(model, generation))


def create_listener(model, *, generation=None):
    model.listener_created(generation=_generation(model, generation))


def append_response(model, *, generation=None):
    model.append_succeeded(generation=_generation(model, generation))


def release_local_entry(model, *, generation=None):
    model.release_entry_local(generation=_generation(model, generation))


def start_transmission(model, *, generation=None):
    model.transmission_started(generation=_generation(model, generation))


def fail_transmission(model, *, known_output_bytes, generation=None):
    model.transmission_failed(known_output_bytes=known_output_bytes,
                              generation=_generation(model, generation))


def write_parent(model, phase, *, known_output_bytes=None, generation=None):
    model.retryable_write(phase, known_output_bytes=known_output_bytes,
                          generation=_generation(model, generation))


def complete_transport(model, *, generation=None):
    model.transport_completed(generation=_generation(model, generation))


def accept_media(model, *, generation=None):
    model.accept_socket(generation=_generation(model, generation))


def stock_snapshot(model):
    return (model.type110_active, model.type110_crypto,
            model.center_screen_state, model.audio_active)


def ready_child():
    model = SyntheticResponseDelivery()
    model.allocate()
    create_listener(model)
    append_response(model)
    release_local_entry(model)
    return model


def connected_child():
    model = ready_child()
    serialize(model, b"synthetic-parent-http-response")
    start_transmission(model)
    complete_transport(model)
    accept_media(model)
    return model


def prepared_child():
    model = SyntheticResponseDelivery()
    model.allocate()
    create_listener(model)
    append_response(model)
    return model


def test_serialized_history_survives_cleanup_and_transport_outcomes():
    model = prepared_child()
    serialize(model, b"synthetic-plist-type110-and-111")
    payload = model.serialized_bytes
    assert model.delivery_state is DeliveryState.SERIALIZED_LOCAL
    model.project_failure("cleanup-after-serialization", generation=model.generation)
    assert model.serialized_bytes == payload
    assert model.type111_in_serialized_response
    assert model.delivery_state is DeliveryState.SEND_FAILED_NO_OUTPUT
    assert model.known_output_bytes == 0 and model.transmission_terminal
    assert model.close_count == model.decoder_release_count == 1
    with pytest.raises(RuntimeError, match="cannot transmit response after Type111 listener cleanup"):
        start_transmission(model)

    uncertain = prepared_child()
    serialize(uncertain, b"synthetic-plist-type110-and-111")
    start_transmission(uncertain)
    fail_transmission(uncertain, known_output_bytes=7)
    assert uncertain.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert uncertain.known_output_bytes == 7
    uncertain.project_failure("cleanup-after-uncertain-send", generation=uncertain.generation)
    assert uncertain.transmission_terminal
    assert uncertain.known_output_bytes is None
    assert not uncertain.listener_open
    assert uncertain.serialized_bytes is not None and uncertain.type110_active


def test_listener_creation_is_single_and_precedes_serialization():
    model = SyntheticResponseDelivery()
    model.allocate()
    create_listener(model)
    with pytest.raises(RuntimeError):
        create_listener(model)

    serialize(model, b"synthetic-response")
    with pytest.raises(RuntimeError):
        create_listener(model)
    assert model.type110_active and model.audio_active


def test_serialization_failure_and_transport_completion_are_distinct():
    failed = prepared_child()
    fail_serialization(failed)
    assert failed.delivery_state is DeliveryState.SERIALIZATION_FAILED
    assert failed.serialized_bytes is None
    assert not failed.response_graph_live and not failed.entry_array_owned
    assert failed.graph_release_count == 1
    assert failed.close_count == failed.decoder_release_count == 1

    no_output = prepared_child()
    serialize(no_output, b"wire")
    start_transmission(no_output)
    fail_transmission(no_output, known_output_bytes=0)
    assert no_output.delivery_state is DeliveryState.SEND_FAILED_NO_OUTPUT
    assert no_output.serialized_bytes == b"wire"

    already_unknown = prepared_child()
    serialize(already_unknown, b"wire")
    start_transmission(already_unknown)
    fail_transmission(already_unknown, known_output_bytes=None)
    assert already_unknown.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert not already_unknown.write_progress_known and already_unknown.transmission_terminal
    assert already_unknown.known_output_bytes is None
    assert not already_unknown.listener_open and not already_unknown.decoder_live
    with pytest.raises(RuntimeError, match="transmission progress is no longer writable"):
        fail_transmission(already_unknown, known_output_bytes=0)
    assert "transmission-failed-no-output" not in already_unknown.events

    complete = prepared_child()
    serialize(complete, b"complete-synthetic-plist")
    start_transmission(complete)
    complete_transport(complete)
    assert complete.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    assert complete.known_output_bytes == len(complete.serialized_bytes)
    assert complete.peer_acceptance == "UNKNOWN"


def test_uncertain_partial_write_can_later_complete_locally_without_peer_ack():
    model = prepared_child()
    serialize(model, b"synthetic-wire")
    write_parent(model, "partial-write", known_output_bytes=3)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.known_output_bytes == 3
    complete_transport(model)
    assert model.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    assert model.peer_acceptance == "UNKNOWN"


def test_terminal_zero_progress_after_partial_write_retains_uncertain_delivery():
    model = prepared_child()
    serialize(model, b"synthetic-wire")
    write_parent(model, "partial-write", known_output_bytes=3)
    fail_transmission(model, known_output_bytes=0)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_offset == model.known_output_bytes == 3
    assert "transmission-failed-delivery-unknown" in model.events
    assert "transmission-failed-no-output" not in model.events


def test_repeated_transmission_start_cannot_reset_partial_delivery_history():
    model = prepared_child()
    serialize(model, b"synthetic-wire")
    write_parent(model, "partial-write", known_output_bytes=3)
    with pytest.raises(RuntimeError, match="cannot transmit before local serialization"):
        start_transmission(model)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_offset == model.known_output_bytes == 3


def test_serialization_failure_cannot_overwrite_serialized_delivery_history():
    model = prepared_child()
    serialize(model, b"synthetic-wire")
    write_parent(model, "partial-write", known_output_bytes=3)
    before = (model.delivery_state, model.serialized_bytes, model.transmission_offset,
              model.known_output_bytes, model.close_count, model.decoder_release_count)
    with pytest.raises(RuntimeError, match="serialization failure requires a pending parent response"):
        fail_serialization(model)
    assert (model.delivery_state, model.serialized_bytes, model.transmission_offset,
            model.known_output_bytes, model.close_count, model.decoder_release_count) == before


def test_response_insertion_cannot_rewrite_serialized_delivery_history():
    model = prepared_child()
    serialize(model, b"wire-a")
    start_transmission(model)
    before = (model.delivery_state, model.serialized_bytes, model.transmission_offset)
    with pytest.raises(RuntimeError, match="response insertion requires an unprepared entry and ready listener"):
        append_response(model)
    assert (model.delivery_state, model.serialized_bytes, model.transmission_offset) == before
    with pytest.raises(RuntimeError, match="serialization failure requires a pending parent response"):
        fail_serialization(model)
    with pytest.raises(RuntimeError, match="parent response is not available for serialization"):
        serialize(model, b"wire-b")
    assert (model.delivery_state, model.serialized_bytes, model.transmission_offset) == before


def test_response_insertion_requires_listener_readiness():
    model = SyntheticResponseDelivery()
    model.allocate()
    before = (model.delivery_state, model.entry_array_owned, model.response_graph_live,
              list(model.events))
    with pytest.raises(RuntimeError, match="response insertion requires an unprepared entry and ready listener"):
        append_response(model)
    assert (model.delivery_state, model.entry_array_owned, model.response_graph_live,
            model.events) == before
    assert not model.listener_open


def test_response_insertion_requires_an_unprepared_project_entry():
    model = prepared_child()
    with pytest.raises(RuntimeError, match="response insertion requires an unprepared entry and ready listener"):
        append_response(model)
    assert model.delivery_state is DeliveryState.PREPARED
    assert model.entry_array_owned


def test_child_resources_cannot_be_allocated_or_accepted_twice():
    model = SyntheticResponseDelivery()
    model.allocate()
    with pytest.raises(RuntimeError, match="previous child resources are still live"):
        model.allocate()
    create_listener(model)
    append_response(model)
    with pytest.raises(RuntimeError, match="accept requires a completed parent response and open listener"):
        accept_media(model)
    serialize(model, b"setup-response")
    start_transmission(model)
    complete_transport(model)
    accept_media(model)
    with pytest.raises(RuntimeError, match="accept requires a completed parent response and open listener"):
        accept_media(model)
    assert model.accepted_socket_open


def test_type110_only_serialization_releases_child_without_advertising_type111():
    model = SyntheticResponseDelivery()
    model.allocate()
    create_listener(model)
    serialize(model, b"synthetic-type110-only-response")
    start_transmission(model)
    complete_transport(model)
    assert not model.type111_in_serialized_response
    assert not model.listener_open and not model.decoder_live
    with pytest.raises(RuntimeError, match="accept requires a completed parent response and open listener"):
        accept_media(model)


@pytest.mark.parametrize("byte_count", [True, 1.5])
def test_non_integer_write_counts_are_rejected_without_state_changes(byte_count):
    model = prepared_child()
    serialize(model, b"wire")
    before = (model.delivery_state, model.known_output_bytes, model.transmission_offset,
              list(model.events))
    with pytest.raises(TypeError, match="known output byte count must be an integer"):
        write_parent(model, "invalid-count", known_output_bytes=byte_count)
    assert (model.delivery_state, model.known_output_bytes, model.transmission_offset,
            model.events) == before


def test_transmission_start_after_http_finalization_reports_closed_connection():
    model = ready_child()
    serialize(model, b"wire")
    model.parent_connection_finalized()
    with pytest.raises(RuntimeError, match="cannot transmit after parent connection finalization"):
        start_transmission(model)


@pytest.mark.parametrize("terminal", [False, True])
def test_write_progress_cannot_exceed_serialized_payload_length(terminal):
    model = prepared_child()
    payload = b"wire"
    serialize(model, payload)
    write_parent(model, "partial-write", known_output_bytes=3)
    before = (model.delivery_state, model.transmission_offset, model.known_output_bytes)
    with pytest.raises(ValueError, match="known output exceeds serialized payload length"):
        if terminal:
            fail_transmission(model, known_output_bytes=2)
        else:
            write_parent(model, "over-reported-write", known_output_bytes=2)
    assert (model.delivery_state, model.transmission_offset, model.known_output_bytes) == before


def test_invalid_first_write_count_does_not_start_transmission_or_record_progress():
    model = prepared_child()
    serialize(model, b"wire")
    before_events = list(model.events)
    with pytest.raises(ValueError, match="known output exceeds serialized payload length"):
        write_parent(model, "invalid-first-write", known_output_bytes=5)
    assert model.delivery_state is DeliveryState.SERIALIZED_LOCAL
    assert model.transmission_offset == 0 and model.known_output_bytes is None
    assert model.events == before_events


def test_parent_teardown_before_serialization_discards_staged_graph_and_rejects_serialize():
    model = prepared_child()
    model.honda_parent_teardown()
    assert model.delivery_state is DeliveryState.FAILED_BEFORE_SERIALIZATION
    assert not model.response_graph_live and not model.entry_array_owned
    assert model.graph_release_count == 1
    with pytest.raises(RuntimeError, match="parent response is not available for serialization"):
        serialize(model, b"late-response")


def test_parent_connection_finalization_fences_pending_http_transmission():
    model = prepared_child()
    serialize(model, b"wire")
    start_transmission(model)
    write_parent(model, "partial-write", known_output_bytes=2)
    model.parent_connection_finalized()
    assert not model.parent_connection_open and model.transmission_terminal
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    with pytest.raises(RuntimeError, match="retryable write requires an active transmission"):
        write_parent(model, "late-retry", known_output_bytes=1)
    with pytest.raises(RuntimeError, match="terminal transmission failure cannot complete"):
        complete_transport(model)
    with pytest.raises(RuntimeError, match="transmission progress is no longer writable"):
        fail_transmission(model, known_output_bytes=0)


def test_parent_connection_finalization_blocks_unsent_type111_response():
    model = prepared_child()
    serialize(model, b"serialized-but-not-sent")
    model.parent_connection_finalized()
    assert model.delivery_state is DeliveryState.SEND_FAILED_NO_OUTPUT
    assert model.serialized_bytes == b"serialized-but-not-sent"
    assert model.transmission_terminal and not model.parent_connection_open
    assert model.parent_teardown_count == 0
    assert model.type110_active and model.audio_active


def test_parent_connection_finalization_with_no_observed_write_progress_is_unknown():
    model = prepared_child()
    serialize(model, b"possibly-in-flight")
    start_transmission(model)
    model.parent_connection_finalized()
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_offset == 0 and model.known_output_bytes is None
    assert model.transmission_terminal and not model.parent_connection_open


def test_session_teardown_does_not_change_completed_http_transport_history():
    model = connected_child()
    model.honda_parent_teardown()
    assert model.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    assert model.parent_connection_open
    assert model.parent_teardown_count == 1
    assert not model.type110_active and not model.audio_active


def test_session_teardown_before_send_fences_serialized_type111_response():
    model = prepared_child()
    serialize(model, b"synthetic-response-with-type111")
    model.honda_parent_teardown()
    assert model.delivery_state is DeliveryState.SEND_FAILED_NO_OUTPUT
    assert model.serialized_bytes == b"synthetic-response-with-type111"
    assert model.type111_in_serialized_response
    assert model.parent_connection_open and model.transmission_terminal
    with pytest.raises(RuntimeError, match="cannot transmit response after Type111 listener cleanup"):
        start_transmission(model)


def test_http_finalization_preserves_completed_type111_media_socket():
    model = prepared_child()
    serialize(model, b"setup-response")
    start_transmission(model)
    write_parent(model, "partial-write", known_output_bytes=4)
    complete_transport(model)
    accept_media(model)
    assert model.accepted_socket_open
    model.parent_connection_finalized()
    assert model.accepted_socket_open
    assert model.socket_close_count == 0
    assert model.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    model.honda_parent_teardown()
    assert not model.accepted_socket_open
    assert model.socket_close_count == 1


def test_child_creation_is_rejected_after_parent_connection_finalization():
    model = prepared_child()
    model.parent_connection_finalized()
    with pytest.raises(RuntimeError, match="child allocation requires an open parent connection"):
        model.allocate()
    with pytest.raises(RuntimeError, match="accept requires a completed parent response and open listener"):
        accept_media(model)


def test_retryable_write_is_rejected_after_terminal_delivery_state():
    model = prepared_child()
    serialize(model, b"wire")
    start_transmission(model)
    complete_transport(model)
    before = (model.delivery_state, model.transmission_offset, model.known_output_bytes,
              list(model.events))
    with pytest.raises(RuntimeError, match="retryable write requires an active transmission"):
        write_parent(model, "late-write", known_output_bytes=1)
    assert (model.delivery_state, model.transmission_offset, model.known_output_bytes,
            model.events) == before


def test_unknown_retryable_write_progress_blocks_retry_from_stale_offset():
    model = prepared_child()
    serialize(model, b"wire-payload")
    write_parent(model, "write-progress-unobservable", known_output_bytes=None)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.known_output_bytes is None
    assert model.transmission_offset == 0 and not model.write_progress_known
    with pytest.raises(RuntimeError, match="cannot retry when write progress is unknown"):
        write_parent(model, "retry-from-stale-offset", known_output_bytes=1)
    assert model.transmission_offset == 0
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN


def test_unknown_retryable_progress_can_record_terminal_error_without_claiming_offset():
    model = prepared_child()
    serialize(model, b"wire-payload")
    write_parent(model, "write-progress-unobservable", known_output_bytes=None)
    with pytest.raises(RuntimeError, match="cannot account for output after write progress became unknown"):
        fail_transmission(model, known_output_bytes=0)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert not model.transmission_terminal
    fail_transmission(model, known_output_bytes=None)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_terminal and not model.write_progress_known
    assert model.known_output_bytes is None
    assert not model.listener_open and not model.decoder_live
    assert model.transmission_offset == 0
    with pytest.raises(RuntimeError, match="terminal transmission failure cannot complete"):
        complete_transport(model)


def test_pre_serialization_child_failure_rolls_back_type111_but_keeps_parent_response():
    model = prepared_child()
    failed_generation = model.generation
    before = stock_snapshot(model)
    model.project_failure("listener-or-authorization-failure", generation=model.generation)
    assert model.generation == failed_generation + 1
    assert model.delivery_state is DeliveryState.NOT_STARTED
    assert model.serialized_bytes is None
    assert model.graph_release_count == 1
    assert not model.response_graph_live and not model.entry_array_owned
    assert not model.listener_open and not model.type111_in_serialized_response
    assert model.close_count == model.decoder_release_count == 1
    with pytest.raises(RuntimeError, match="stale child generation"):
        serialize(model, b"late-stale-type111-response", generation=failed_generation)
    serialize(model, b"synthetic-type110-only-response")
    assert model.delivery_state is DeliveryState.SERIALIZED_LOCAL
    assert not model.type111_in_serialized_response
    assert model.type110_active and model.audio_active
    counts = (model.close_count, model.socket_close_count, model.decoder_release_count)
    model.project_failure("repeat-cleanup", generation=model.generation)
    assert (model.close_count, model.socket_close_count, model.decoder_release_count) == counts
    assert stock_snapshot(model) == before


def test_project_allocation_and_listener_creation_failures_are_local():
    model = SyntheticResponseDelivery()
    before = stock_snapshot(model)
    model.project_failure("project-allocation-failure", generation=model.generation)
    assert not model.entry_local and model.close_count == 0
    assert stock_snapshot(model) == before
    model = SyntheticResponseDelivery()
    model.allocate()
    before = stock_snapshot(model)
    model.project_failure("listener-creation-failure", generation=model.generation)
    assert model.decoder_release_count == 1 and model.close_count == 0
    assert stock_snapshot(model) == before


def test_listener_ready_child_rollback_before_insertion_preserves_parent_response():
    model = SyntheticResponseDelivery()
    model.allocate()
    create_listener(model)
    failed_generation = model.generation
    before = stock_snapshot(model)
    model.project_failure("failure-before-response-insertion", generation=model.generation)
    assert model.generation == failed_generation + 1
    assert model.close_count == model.decoder_release_count == 1
    assert model.socket_close_count == 0
    assert not model.entry_local and not model.entry_array_owned
    with pytest.raises(RuntimeError, match="stale child generation"):
        serialize(model, b"late-stale-type111-response", generation=failed_generation)
    serialize(model, b"synthetic-type110-only-response")
    assert model.serialized_bytes == b"synthetic-type110-only-response"
    assert not model.type111_in_serialized_response
    assert stock_snapshot(model) == before


def test_serialization_failure_cleans_child_without_changing_parent():
    model = ready_child()
    before = stock_snapshot(model)
    fail_serialization(model)
    assert model.delivery_state is DeliveryState.SERIALIZATION_FAILED
    assert not model.response_graph_live
    assert model.close_count == model.decoder_release_count == 1
    assert model.socket_close_count == 0
    assert stock_snapshot(model) == before


def test_cleanup_after_serialization_preserves_delivery_history():
    model = ready_child()
    serialize(model, b"synthetic-wire")
    before = stock_snapshot(model)
    model.project_failure("cleanup-after-serialization", generation=model.generation)
    assert model.delivery_state is DeliveryState.SEND_FAILED_NO_OUTPUT
    assert model.serialized_bytes == b"synthetic-wire"
    assert model.type111_in_serialized_response
    assert model.known_output_bytes == 0 and model.transmission_terminal
    assert model.close_count == model.decoder_release_count == 1
    assert model.socket_close_count == 0
    assert stock_snapshot(model) == before


def test_partial_and_retryable_writes_remain_pending():
    for phase in ("partial-write", "retryable-eagain"):
        model = ready_child()
        serialize(model, b"synthetic-wire")
        before = stock_snapshot(model)
        write_parent(model, phase, known_output_bytes=2 if phase == "partial-write" else 0)
        assert model.listener_open and model.decoder_live
        assert not model.accepted_socket_open
        assert model.delivery_state is (DeliveryState.DELIVERY_UNKNOWN if phase == "partial-write"
                                        else DeliveryState.TRANSMISSION_STARTED)
        assert model.transmission_offset == (2 if phase == "partial-write" else 0)
        assert stock_snapshot(model) == before


def test_consecutive_eagain_then_progress_and_completion_preserves_offset():
    model = ready_child()
    payload = b"abcdef"
    serialize(model, payload)
    write_parent(model, "eagain-1", known_output_bytes=0)
    write_parent(model, "eagain-2", known_output_bytes=0)
    assert model.delivery_state is DeliveryState.TRANSMISSION_STARTED
    assert not model.transmission_terminal and model.known_output_bytes == 0
    assert model.serialized_bytes == payload and model.transmission_offset == 0
    write_parent(model, "write-prefix", known_output_bytes=2)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_offset == 2 and model.serialized_bytes == payload
    write_parent(model, "write-suffix", known_output_bytes=4)
    assert model.transmission_offset == len(payload)
    complete_transport(model)
    assert model.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    assert model.peer_acceptance == "UNKNOWN"


def test_cleanup_during_retry_preserves_delivery_history_and_stock():
    model = ready_child()
    serialize(model, b"pending-wire")
    write_parent(model, "eagain", known_output_bytes=0)
    before = stock_snapshot(model)
    model.project_failure("cancel-pending-send", generation=model.generation)
    counts = (model.close_count, model.socket_close_count, model.decoder_release_count)
    model.project_failure("repeat-cancel", generation=model.generation)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert model.transmission_terminal and model.known_output_bytes is None
    assert model.serialized_bytes == b"pending-wire"
    assert (model.close_count, model.socket_close_count, model.decoder_release_count) == counts
    assert stock_snapshot(model) == before


def test_stale_generation_cleanup_cannot_close_current_type111_resources():
    model = prepared_child()
    stale_generation = model.generation
    model.project_failure("first-generation-rollback", generation=stale_generation)
    model.allocate()
    create_listener(model)
    append_response(model)
    release_local_entry(model)
    assert model.generation > stale_generation + 1
    before = (model.listener_open, model.accepted_socket_open, model.decoder_live,
              model.close_count, model.socket_close_count, model.decoder_release_count)
    model.project_failure("late-generation-cleanup", generation=stale_generation)
    assert (model.listener_open, model.accepted_socket_open, model.decoder_live,
            model.close_count, model.socket_close_count, model.decoder_release_count) == before
    assert model.type110_active and model.audio_active


def test_cleanup_from_preallocation_generation_cannot_close_first_child():
    model = SyntheticResponseDelivery()
    stale_generation = model.generation
    model.project_failure("failed-allocation-attempt", generation=stale_generation)
    model.allocate()
    create_listener(model)
    append_response(model)
    release_local_entry(model)
    assert model.generation == stale_generation + 1
    before = (model.listener_open, model.decoder_live, model.close_count,
              model.decoder_release_count, model.entry_array_owned)
    model.project_failure("late-failed-allocation-cleanup", generation=stale_generation)
    assert (model.listener_open, model.decoder_live, model.close_count,
            model.decoder_release_count, model.entry_array_owned) == before
    assert "late-failed-allocation-cleanup" not in model.events


def test_future_cleanup_generation_is_rejected_without_state_changes():
    model = ready_child()
    before = (model.delivery_state, model.listener_open, model.decoder_live,
              model.response_graph_live, list(model.events))
    with pytest.raises(RuntimeError, match="cleanup generation is from the future"):
        model.project_failure("future-cleanup", generation=model.generation + 1)
    assert (model.delivery_state, model.listener_open, model.decoder_live,
            model.response_graph_live, model.events) == before


def test_stale_child_callbacks_cannot_mutate_reallocated_generation():
    model = prepared_child()
    stale_generation = model.generation
    model.project_failure("first-generation-rollback", generation=stale_generation)
    model.allocate()
    current_generation = model.generation
    with pytest.raises(RuntimeError, match="stale child generation"):
        create_listener(model, generation=stale_generation)
    assert not model.listener_open
    create_listener(model, generation=current_generation)
    with pytest.raises(RuntimeError, match="stale child generation"):
        append_response(model, generation=stale_generation)
    append_response(model, generation=current_generation)
    with pytest.raises(RuntimeError, match="stale child generation"):
        fail_serialization(model, generation=stale_generation)
    with pytest.raises(RuntimeError, match="stale child generation"):
        serialize(model, b"stale-response", generation=stale_generation)
    assert model.delivery_state is DeliveryState.PREPARED
    assert model.listener_open and model.entry_array_owned

    release_local_entry(model, generation=current_generation)
    serialize(model, b"current-response", generation=current_generation)
    start_transmission(model, generation=current_generation)
    complete_transport(model, generation=current_generation)
    with pytest.raises(RuntimeError, match="stale child generation"):
        accept_media(model, generation=stale_generation)
    assert not model.accepted_socket_open
    accept_media(model, generation=current_generation)
    assert model.accepted_socket_open


def test_missing_cleanup_generation_is_rejected_before_mutating_state():
    model = ready_child()
    before = (model.delivery_state, model.listener_open, model.decoder_live,
              model.response_graph_live, list(model.events))
    with pytest.raises(ValueError, match="cleanup generation must be a nonnegative integer"):
        model.project_failure("missing-generation", generation=None)
    assert (model.delivery_state, model.listener_open, model.decoder_live,
            model.response_graph_live, model.events) == before


def test_terminal_write_failure_marks_delivery_unknown_without_parent_teardown():
    model = ready_child()
    serialize(model, b"synthetic-wire")
    start_transmission(model)
    before = stock_snapshot(model)
    fail_transmission(model, known_output_bytes=None)
    assert model.delivery_state is DeliveryState.DELIVERY_UNKNOWN
    assert not model.write_progress_known and model.transmission_terminal
    assert model.known_output_bytes is None
    assert not model.listener_open and not model.decoder_live
    assert model.type111_in_serialized_response
    assert model.type110_active and model.audio_active
    assert stock_snapshot(model) == before


def test_connection_finalize_and_parent_teardown_keep_child_cleanup_idempotent():
    model = connected_child()
    assert model.accepted_socket_open
    model.parent_connection_finalized()
    assert not model.parent_connection_open
    assert model.accepted_socket_open and model.socket_close_count == 0
    assert model.delivery_state is DeliveryState.TRANSPORT_COMPLETE
    after_first = (model.close_count, model.socket_close_count,
                   model.decoder_release_count, model.parent_teardown_count)
    model.honda_parent_teardown()
    assert not model.accepted_socket_open and model.socket_close_count == 1
    assert model.close_count == after_first[0] + 1
    assert model.decoder_release_count == after_first[2] + 1
    assert model.parent_teardown_count == after_first[3] + 1
    assert not model.type110_active and not model.audio_active
    assert model.center_screen_state == "honda-parent-torn-down"
    after_teardown = (model.close_count, model.socket_close_count,
                      model.decoder_release_count, model.parent_teardown_count)
    model.honda_parent_teardown()
    assert (model.close_count, model.socket_close_count,
            model.decoder_release_count, model.parent_teardown_count) == after_teardown


def test_repeated_teardown_and_already_stopped_child_are_idempotent():
    model = ready_child()
    model.project_failure("project-only-stop", generation=model.generation)
    counts = (model.close_count, model.socket_close_count, model.decoder_release_count)
    model.honda_parent_teardown()
    model.honda_parent_teardown()
    assert (model.close_count, model.socket_close_count, model.decoder_release_count) == counts
    assert model.parent_teardown_count == 1


def test_parent_session_teardown_still_applies_after_http_finalization():
    model = ready_child()
    model.parent_connection_finalized()
    assert model.parent_connection_open is False
    assert model.type110_active and model.audio_active
    model.honda_parent_teardown()
    assert model.parent_connection_open is False
    assert model.parent_teardown_count == 1
    assert model.type110_active is False and model.audio_active is False


def test_project_only_failure_preserves_type110_crypto_screen_and_audio():
    model = ready_child()
    before = stock_snapshot(model)
    model.project_failure("project-only-runtime-failure", generation=model.generation)
    assert stock_snapshot(model) == before


def test_honda_parent_teardown_is_the_only_modeled_stock_state_transition():
    model = ready_child()
    before = stock_snapshot(model)
    model.project_failure("project-only-stop", generation=model.generation)
    assert stock_snapshot(model) == before
    model.honda_parent_teardown()
    assert model.type110_active is False and model.audio_active is False
    assert model.center_screen_state == "honda-parent-torn-down"
    assert model.type110_crypto == before[1]
    assert model.events.count("honda-parent-session-teardown") == 1
