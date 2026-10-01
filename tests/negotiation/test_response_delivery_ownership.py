"""Synthetic-only project child ownership and response delivery failures."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from response_delivery_model import SyntheticResponseDelivery


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
        model.serialized()
        before = stock_snapshot(model)
        model.project_failure(phase)
        assert not model.response_graph_live
        assert model.close_count == model.socket_close_count == model.decoder_release_count == 1
        assert stock_snapshot(model) == before
        assert_project_did_not_mutate_stock(model)


def test_partial_and_retryable_writes_remain_pending():
    for phase in ("partial-write", "retryable-eagain"):
        model = ready_child()
        model.serialized()
        before = stock_snapshot(model)
        model.retryable_write(phase)
        assert model.listener_open and model.accepted_socket_open and model.decoder_live
        assert stock_snapshot(model) == before
        assert_project_did_not_mutate_stock(model)


def test_terminal_write_error_or_peer_disconnect_waits_for_parent_teardown_event():
    for phase in ("terminal-write-error", "peer-disconnect"):
        model = ready_child()
        model.serialized()
        before = stock_snapshot(model)
        model.retryable_write(phase)  # delivery failure and session teardown are separate events
        assert model.listener_open and model.type110_active and model.audio_active
        assert stock_snapshot(model) == before


def test_connection_finalize_then_parent_teardown_cleans_child_once():
    model = ready_child()
    model.serialized()
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
