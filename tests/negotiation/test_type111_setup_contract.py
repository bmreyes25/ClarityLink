import sys
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "src/claritylink-transport"),
    str(ROOT / "src/claritylink-negotiation"),
    str(ROOT / "src/carplay-session-model"),
]

from dual_screen_lifecycle import DualScreenLifecycleTwin
from legacy_dual_screen_twin import LegacyDualScreenTwin, ScreenRole
from project_lifecycle import ChildPhase
from type111_setup_contract import (
    DeterministicListenerAllocator,
    ListenerState,
    SerializerResult,
    Type111SetupContract,
    parse_setup_request,
)


def _twin():
    screens = LegacyDualScreenTwin(bytes(range(16)), encrypt_block=lambda k, c: bytes(a ^ b for a, b in zip(k, c)))
    a = screens.add_screen(ScreenRole.TYPE110, 1101)
    return DualScreenLifecycleTwin(screens), a


def _serializer(result=SerializerResult(0xC8, 0)):
    calls = []
    def invoke(response):
        calls.append(response)
        return result
    return calls, invoke


def test_type111_first_and_type110_first_preserve_request_order_and_unknown_fields():
    for order in ((111, 110), (110, 111)):
        parsed = parse_setup_request({"streams": [
            {"type": kind, "streamConnectionID": 2201 if kind == 111 else 1101, "opaque": "synthetic"}
            for kind in order
        ]})
        assert [item.stream_type for item in parsed] == list(order)
        assert [item.request_index for item in parsed] == [0, 1]
        assert parsed[0].fields["opaque"] == "synthetic"


def test_sanitized_43p_shaped_fixture_runs_as_type111_first_contract():
    fixture = json.loads((ROOT / "research/simulator/43r-type111-first-setup.json").read_text())
    lifecycle, _ = _twin()
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, DeterministicListenerAllocator()).process(
        fixture["request"], fixture["stock_response"], serializer
    )
    assert [entry["type"] for entry in fixture["request"]["streams"]] == [111, 110]
    assert result.committed and result.serializer_invocations == len(calls) == 1
    assert result.response["streams"][-1] == fixture["expected_project_response_append"]


@pytest.mark.parametrize("input_request", [
    {"streams": [{"type": 110, "streamConnectionID": 1101}]},
    {"streams": [{"type": 111, "streamConnectionID": 2201}]},
    {"streams": [{"type": 111, "streamConnectionID": 2201}, {"type": 110, "streamConnectionID": 1101}]},
    {"streams": [{"type": 110, "streamConnectionID": 1101}, {"type": 111, "streamConnectionID": 2201}]},
])
def test_supported_shapes_serialize_once_and_keep_stock_type110_entry(input_request):
    lifecycle, a = _twin()
    allocator = DeterministicListenerAllocator()
    contract = Type111SetupContract(lifecycle, allocator)
    stock = {"streams": [{"type": 110, "dataPort": 41100, "opaque": {"keep": True}}], "stock": "same"}
    before = repr(a)
    calls, serializer = _serializer()
    result = contract.process(input_request, stock, serializer)
    assert result.serializer_invocations == len(calls) == 1
    assert result.serializer_result == SerializerResult(0xC8, 0)
    assert result.committed
    assert result.response["streams"][0] == stock["streams"][0]
    if any(stream["type"] == 111 for stream in input_request["streams"]):
        assert result.generation == 1
        assert result.listener_id == 1 and result.data_port == 41000
        assert result.response["streams"][-1] == {"type": 111, "dataPort": 41000}
        assert lifecycle.current_type111.phase is ChildPhase.ACTIVE
        assert allocator.reservations[0].state is ListenerState.LISTENING
        assert allocator.reservations[0].role is ScreenRole.TYPE111_SYNTHETIC
        assert allocator.reservations[0].owner_key == lifecycle.current_type111.key
    else:
        assert result.generation is None and result.response == stock
    assert repr(a) == before and a.active


def test_duplicate_screen_id_reuses_structured_error_and_allocates_no_listener():
    lifecycle, _ = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 1101}]}, {"streams": []}, serializer
    )
    assert result.error_code == "duplicate_stream_connection_id"
    assert result.serializer_invocations == len(calls) == 1
    assert not allocator.reservations and lifecycle.current_type111 is None


@pytest.mark.parametrize("input_request", [
    {"streams": [{"type": 111}]},
    {"streams": [{"type": 111, "streamConnectionID": True}]},
    {"streams": [{"type": 111, "streamConnectionID": "synthetic-id"}]},
    {"streams": [{"type": 111, "streamConnectionID": 1}, {"type": 111, "streamConnectionID": 2}]},
])
def test_malformed_request_fails_closed_and_invokes_stock_serializer_once(input_request):
    lifecycle, _ = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer()
    stock = {"streams": [{"type": 110, "dataPort": 41100}]}
    result = Type111SetupContract(lifecycle, allocator).process(input_request, stock, serializer)
    assert result.error_code
    assert result.serializer_invocations == len(calls) == 1
    assert calls[0] == stock and not allocator.reservations
    assert lifecycle.current_type111 is None


def test_unknown_stream_type_in_type111_request_fails_closed_without_listener():
    lifecycle, _ = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": 999, "streamConnectionID": 8}, {"type": 111, "streamConnectionID": 2201}]},
        {"streams": []}, serializer,
    )
    assert result.error_code == "unsupported_stream_type_for_type111_adapter"
    assert result.serializer_invocations == len(calls) == 1
    assert not allocator.reservations and lifecycle.current_type111 is None


@pytest.mark.parametrize("stock", [{"streams": "not-an-array"}, []])
def test_invalid_stock_response_fails_closed_without_listener_and_calls_serializer_once(stock):
    lifecycle, _ = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer()
    request = {"streams": [{"type": 111, "streamConnectionID": 2201}]}
    result = Type111SetupContract(lifecycle, allocator).process(request, stock, serializer)
    assert result.error_code == "stock_response_streams_invalid" if isinstance(stock, dict) else result.error_code == "stock_response_must_be_mapping"
    assert result.serializer_invocations == len(calls) == 1
    assert not allocator.reservations and lifecycle.current_type111 is None


def test_listener_failure_and_mutation_failure_roll_back_exact_generation():
    for allocator, mutate in (
        (DeterministicListenerAllocator(fail_at="bind"), False),
        (DeterministicListenerAllocator(first_port=0), False),
        (DeterministicListenerAllocator(fail_at="closed_before_commit"), False),
        (DeterministicListenerAllocator(), True),
    ):
        lifecycle, a = _twin()
        calls, serializer = _serializer()
        result = Type111SetupContract(lifecycle, allocator).process(
            {"streams": [{"type": 111, "streamConnectionID": 2201}]},
            {"streams": [{"type": 110, "dataPort": 41100}]}, serializer,
            fail_response_mutation=mutate,
        )
        assert result.serializer_invocations == len(calls) == 1
        assert calls[0]["streams"] == [{"type": 110, "dataPort": 41100}]
        assert lifecycle.current_type111 is None and a.active
        if allocator.reservations:
            assert allocator.reservations[0].state is ListenerState.CLOSED
            assert allocator.reservations[0].close_count == 1


@pytest.mark.parametrize("serializer_result", [SerializerResult(0xC8, 1), SerializerResult(500, 0), SerializerResult(500, 9)])
def test_serializer_failure_preserves_result_and_cleans_only_exact_b(serializer_result):
    lifecycle, a = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer(serializer_result)
    stock = {"streams": [{"type": 110, "dataPort": 41100, "keep": 1}]}
    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock, serializer
    )
    assert result.serializer_invocations == len(calls) == 1
    assert result.serializer_result == serializer_result
    assert not result.committed and result.error_code == "stock_serializer_failed"
    assert result.response["streams"][0] == stock["streams"][0]
    assert lifecycle.current_type111 is None and a.active
    assert allocator.reservations[0].state is ListenerState.CLOSED


def test_new_generation_and_stale_old_listener_cleanup_are_exact_instance_scoped():
    lifecycle, a = _twin()
    allocator = DeterministicListenerAllocator()
    contract = Type111SetupContract(lifecycle, allocator)
    stock = {"streams": []}
    _, ok = _serializer()
    first = contract.process({"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock, ok)
    old_listener = allocator.reservations[0]
    b1 = lifecycle.current_type111
    assert b1.teardown()
    second = contract.process({"streams": [{"type": 111, "streamConnectionID": 2202}]}, stock, ok)
    b2 = lifecycle.current_type111
    assert second.generation > first.generation
    assert not b1.teardown()
    old_listener.close()
    assert b2.phase is ChildPhase.ACTIVE
    assert allocator.reservations[1].state is ListenerState.LISTENING
    assert a.active


def test_diagnostics_do_not_return_raw_synthetic_ids_or_secret_material():
    lifecycle, _ = _twin()
    calls, serializer = _serializer()
    raw_id = 987654321
    result = Type111SetupContract(lifecycle, DeterministicListenerAllocator()).process(
        {"streams": [{"type": 111, "streamConnectionID": raw_id}]}, {"streams": []}, serializer
    )
    assert str(raw_id) not in repr(result)
    assert "key" not in repr(result).lower()
