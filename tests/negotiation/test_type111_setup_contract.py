import json
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "src/claritylink-transport"),
    str(ROOT / "src/claritylink-negotiation"),
    str(ROOT / "src/carplay-session-model"),
    str(ROOT / "src/claritylink-interposer"),
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
from real_listener import InterfaceKind, InterfacePolicy, RealListenerAllocator


def _twin():
    screens = LegacyDualScreenTwin(bytes(range(16)), encrypt_block=lambda k, c: bytes(a ^ b for a, b in zip(k, c)))
    a = screens.add_screen(ScreenRole.TYPE110, 1101)
    return DualScreenLifecycleTwin(screens), a


def _synthetic_contract(lifecycle, allocator):
    return Type111SetupContract(
        lifecycle, allocator, enable_synthetic_type111_for_tests=True
    )


def _serializer(result=SerializerResult(0xC8, 0)):
    calls = []
    def invoke(response):
        calls.append(response)
        return result
    return calls, invoke


def test_real_host_listener_is_ready_before_stock_serializer_and_owned_by_generation():
    lifecycle, type110 = _twin()
    allocator = RealListenerAllocator(InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
    stock = {"streams": [{"type": 110, "dataPort": 41001}], "audio": "stock"}
    calls = []
    client = None

    def serializer(response):
        listener = allocator.reservations[0]
        assert listener.state == "READY"
        assert listener.sock.getsockname()[1] == response["streams"][-1]["dataPort"]
        calls.append(response)
        return SerializerResult(0xC8, 0)

    result = _synthetic_contract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock, serializer
    )
    listener = allocator.reservations[0]
    try:
        assert result.committed and result.serializer_invocations == len(calls) == 1
        assert result.data_port == listener.port
        assert result.response["streams"][0] == stock["streams"][0]
        assert type110.active and lifecycle.current_type111.phase is ChildPhase.ACTIVE
        # A client can connect as soon as the stock serialization boundary returns.
        client = socket.socket()
        client.connect(("127.0.0.1", result.data_port))
        accepted = listener.wait_accepted()
        assert accepted is not None
        assert lifecycle.current_type111.teardown()
        assert listener.sock.fileno() == -1 and accepted.fileno() == -1
        assert listener.close_count == 1 and not listener.worker.is_alive()
    finally:
        if client is not None:
            client.close()
        if listener.state != "CLOSED":
            listener.close()


def test_real_listener_failure_and_serializer_failure_roll_back_once():
    lifecycle, type110 = _twin()
    stock = {"streams": [{"type": 110, "dataPort": 41001}]}
    calls = []

    def serializer(response):
        calls.append(response)
        return SerializerResult(0x1F4, 1)

    allocator = RealListenerAllocator(InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
    result = _synthetic_contract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock, serializer
    )
    listener = allocator.reservations[0]
    assert not result.committed and len(calls) == result.serializer_invocations == 2
    assert calls[0]["streams"][0] == stock["streams"][0]
    assert calls[0]["streams"][-1]["type"] == 111
    assert calls[1] == stock
    assert result.serializer_result == SerializerResult(0x1F4, 1)
    assert result.candidate_serializer_result == SerializerResult(0x1F4, 1)
    assert listener.state == "CLOSED" and listener.sock.fileno() == -1
    assert listener.close_count == 1 and not listener.worker.is_alive()
    assert result.security_mode == "SYNTHETIC_TEST_ONLY"
    assert lifecycle.current_type111 is None and type110.active

    failed_lifecycle, failed_type110 = _twin()
    for phase, stream_id in (("listen", 3301), ("accept", 3302)):
        failed_lifecycle, failed_type110 = _twin()
        failed_allocator = RealListenerAllocator(
            InterfacePolicy(InterfaceKind.LOOPBACK_TEST), failure_at=phase)
        failed_calls = []
        failed = _synthetic_contract(failed_lifecycle, failed_allocator).process(
            {"streams": [{"type": 111, "streamConnectionID": stream_id}]}, stock,
            lambda response: (failed_calls.append(response) or SerializerResult(0xC8, 0)),
        )
        assert failed.error_code and failed.serializer_invocations == len(failed_calls) == 1
        assert failed_calls[0] == stock
        assert failed.security_mode == "SYNTHETIC_TEST_ONLY"
        assert not failed_allocator.reservations
        assert failed_lifecycle.current_type111 is None and failed_type110.active


def test_real_listener_commit_failure_and_parent_teardown_close_exact_resources():
    lifecycle, type110 = _twin()
    allocator = RealListenerAllocator(InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
    calls = []

    def superseding_serializer(response):
        calls.append(response)
        if len(calls) == 1:
            lifecycle.current_type111.fail()
        return SerializerResult(0xC8, 0)

    stock = {"streams": [{"type": 110, "dataPort": 41001}]}
    result = _synthetic_contract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 4401}]},
        stock, superseding_serializer,
    )
    listener = allocator.reservations[0]
    assert not result.committed and result.serializer_invocations == len(calls) == 2
    assert result.error_code == "type111_activation_failed"
    assert result.candidate_serializer_result == SerializerResult(0xC8, 0)
    assert result.serializer_result == SerializerResult(0xC8, 0)
    assert result.response == stock and result.data_port is None
    assert not result.response_appended
    assert calls[0]["streams"][-1]["type"] == 111 and calls[1] == stock
    assert listener.sock.fileno() == -1 and listener.close_count == 1
    assert not listener.worker.is_alive() and type110.active

    parent, parent_type110 = _twin()
    parent_allocator = RealListenerAllocator(InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
    parent_result = _synthetic_contract(parent, parent_allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 4402}]},
        {"streams": []}, _serializer()[1],
    )
    parent_listener = parent_allocator.reservations[0]
    assert parent_result.committed
    assert parent.destroy_parent()
    assert parent_listener.sock.fileno() == -1
    assert parent_listener.close_count == 1 and not parent_listener.worker.is_alive()
    assert not parent_type110.active



def test_serializer_copy_failure_falls_back_to_stock_serializer_exactly_once():
    class FailOnSecondDeepcopy:
        def __init__(self):
            self.calls = 0

        def __deepcopy__(self, _memo):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("synthetic copy failure")
            return self

    lifecycle, type110 = _twin()
    opaque = FailOnSecondDeepcopy()
    stock = {"streams": [{"type": 110, "dataPort": 41001}], "opaque": opaque}
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, DeterministicListenerAllocator()).process(
        {"streams": [{"type": 110, "streamConnectionID": 1101}]}, stock, serializer
    )

    assert result.error_code == "project_setup_failed"
    assert result.serializer_invocations == len(calls) == 1
    assert result.response["streams"] == stock["streams"]
    assert calls[0]["streams"] == stock["streams"]
    assert type110.active and lifecycle.current_type111 is None


def test_uncopyable_stock_still_reaches_original_serializer_once_without_type111_changes():
    class UncopyableStockValue:
        def __deepcopy__(self, _memo):
            raise RuntimeError("opaque factory value")

    lifecycle, type110 = _twin()
    opaque = UncopyableStockValue()
    stock = {"streams": [{"type": 110, "dataPort": 41001}], "opaque": opaque}
    calls = []
    result = Type111SetupContract(lifecycle, DeterministicListenerAllocator()).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]},
        stock, lambda response: (calls.append(response) or SerializerResult(0xC8, 0)),
    )

    assert result.error_code == "type111_authority_unavailable"
    assert result.fallback_error_code == "stock_response_copy_failed"
    assert result.serializer_invocations == len(calls) == 1
    assert calls[0] is stock and calls[0]["opaque"] is opaque
    assert result.response is None and not result.committed
    assert result.data_port is None and result.listener_id is None
    assert lifecycle.current_type111 is None and type110.active



def test_activation_exception_preserves_serializer_result_and_stock_snapshot():
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    stock = {"streams": [{"type": 110, "dataPort": 41001}]}
    calls = []
    original_create = lifecycle.create_type111

    def create_with_activation_failure(stream_connection_id):
        generation = original_create(stream_connection_id)
        def fail_activation():
            raise RuntimeError("synthetic activation failure")
        generation.activate = fail_activation
        return generation

    lifecycle.create_type111 = create_with_activation_failure
    result = _synthetic_contract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock,
        lambda response: (calls.append(response) or SerializerResult(0xC8, 0)),
    )

    assert result.error_code == "project_setup_failed"
    assert result.serializer_result == SerializerResult(0xC8, 0)
    assert result.candidate_serializer_result == SerializerResult(0xC8, 0)
    assert result.serializer_invocations == len(calls) == 2
    assert result.response == stock and result.data_port is None
    assert not result.committed and not result.response_appended
    assert lifecycle.current_type111 is None and type110.active
    assert allocator.reservations[0].state is ListenerState.CLOSED


def test_cleanup_exception_is_reported_without_masking_stock_serializer_fallback():
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    stock = {"streams": [{"type": 110, "dataPort": 41001}]}
    calls = []
    original_create = lifecycle.create_type111
    generations = []

    def create_with_cleanup_failure(stream_connection_id):
        generation = original_create(stream_connection_id)
        generations.append(generation)
        original_fail = generation.fail
        generation.fail = lambda: (_ for _ in ()).throw(RuntimeError("close failed"))
        generation.restore_fail = original_fail
        return generation

    lifecycle.create_type111 = create_with_cleanup_failure
    result = _synthetic_contract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 2202}]}, stock,
        lambda response: (calls.append(response) or SerializerResult(0xC8, 0)),
        fail_response_mutation=True,
    )

    assert result.error_code == "response_mutation_failed"
    assert result.cleanup_error_code == "type111_cleanup_failed"
    assert result.response == stock and result.data_port is None
    assert result.generation_lease is not None
    assert result.serializer_invocations == len(calls) == 1
    assert type110.active
    generations[0].fail = generations[0].restore_fail
    assert generations[0].fail()
    assert lifecycle.current_type111 is None

def test_serializer_invalid_result_retains_stock_snapshot_and_specific_error():
    lifecycle, type110 = _twin()
    stock = {"streams": [{"type": 110, "dataPort": 41001}], "factory": True}
    calls = []
    result = Type111SetupContract(lifecycle, DeterministicListenerAllocator()).process(
        {"streams": [{"type": 110, "streamConnectionID": 1101}]}, stock,
        lambda response: (calls.append(response) or {"unexpected": "result"}),
    )

    assert result.error_code == "serializer_result_invalid"
    assert result.response == stock
    assert type110.active and lifecycle.current_type111 is None


def test_post_serializer_mutation_keeps_pre_serializer_factory_snapshot():
    lifecycle, _type110 = _twin()
    stock = {"streams": [{"type": 110, "dataPort": 41001}], "audio": {"owner": "factory"}}
    calls = []

    class OpaqueAfterSerializerMutation:
        def __deepcopy__(self, _memo):
            raise RuntimeError("not copyable")

    def mutate_into_opaque_value(response):
        calls.append(response)
        response["audio"]["opaque"] = OpaqueAfterSerializerMutation()
        return SerializerResult(0xC8, 0)

    result = Type111SetupContract(
        lifecycle, DeterministicListenerAllocator()
    ).process({"streams": "malformed"}, stock, mutate_into_opaque_value)

    assert result.error_code == "request_streams_must_be_array"
    assert result.fallback_error_code == "stock_serializer_mutated_response"
    assert result.serializer_result == SerializerResult(0xC8, 0)
    assert result.response == stock
    assert result.serializer_invocations == len(calls) == 1

def test_default_contract_rejects_type111_without_authenticated_authority_and_preserves_stock():
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    stock = {"streams": [{"type": 110, "dataPort": 41100, "opaque": "factory"}],
             "audio": {"mode": "stock"}}
    calls, serializer = _serializer()

    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock, serializer
    )

    assert result.requested_type111 and not result.committed
    assert result.error_code == "type111_authority_unavailable"
    assert result.security_mode == "TYPE111_DISABLED_AUTHORITY_UNKNOWN"
    assert result.serializer_invocations == len(calls) == 1
    assert result.serializer_result == SerializerResult(0xC8, 0)
    assert calls[0] == stock == result.response
    assert result.data_port is None and result.listener_id is None
    assert not allocator.reservations and lifecycle.current_type111 is None
    assert type110.active


def test_default_type111_fallback_reports_failed_stock_serializer():
    lifecycle, type110 = _twin()
    stock = {"streams": [{"type": 110, "dataPort": 41100}]}
    calls = []
    result = Type111SetupContract(lifecycle, DeterministicListenerAllocator()).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock,
        lambda response: (calls.append(response) or SerializerResult(0x1F4, 1)),
    )

    assert result.error_code == "type111_authority_unavailable"
    assert result.fallback_error_code == "stock_serializer_failed"
    assert result.serializer_result == SerializerResult(0x1F4, 1)
    assert result.serializer_invocations == len(calls) == 1
    assert not result.committed and result.response == stock
    assert lifecycle.current_type111 is None and type110.active


def test_default_authority_gate_passes_malformed_stock_unchanged_to_original_serializer():
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    calls = []
    request = {"streams": [{"type": 111, "streamConnectionID": 2201}]}
    malformed_stock = {"streams": "malformed"}
    result = Type111SetupContract(lifecycle, allocator).process(
        request, malformed_stock,
        lambda response: (calls.append(response) or SerializerResult(0x1F4, 1)),
    )
    assert result.error_code == "stock_response_streams_invalid"
    assert result.security_mode == "TYPE111_DISABLED_AUTHORITY_UNKNOWN"
    assert result.serializer_invocations == len(calls) == 1
    assert calls == [malformed_stock] and result.response == malformed_stock
    assert result.generation is None and result.data_port is None
    assert lifecycle.current_type111 is None and type110.active


def test_default_contract_preserves_factory_type110_without_test_mode():
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    stock = {"streams": [{"type": 110, "dataPort": 41100}], "factory": True}
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": 110, "streamConnectionID": 1101}]}, stock, serializer
    )
    assert result.committed and not result.requested_type111
    assert result.response == stock and calls == [stock]
    assert not allocator.reservations and type110.active


@pytest.mark.parametrize("requested_type", [110, 111])
def test_stock_serializer_mutation_is_rejected_without_changing_factory_snapshot(requested_type):
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    stock = {"streams": [{"type": 110, "dataPort": 41100}], "audio": {"mode": "stock"}}
    calls = []

    def mutating_serializer(response):
        calls.append(response)
        response["audio"]["serializerMutation"] = True
        return SerializerResult(0xC8, 0)

    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": requested_type, "streamConnectionID": 1101 if requested_type == 110 else 2201}]},
        stock, mutating_serializer,
    )

    assert result.serializer_invocations == len(calls) == 1
    assert "serializerMutation" in calls[0]["audio"]
    assert result.response == stock
    assert "serializerMutation" not in result.response["audio"]
    assert "serializerMutation" not in stock["audio"]
    assert type110.active and not allocator.reservations
    if requested_type == 111:
        assert result.error_code == "type111_authority_unavailable"
        assert result.fallback_error_code == "stock_serializer_mutated_response"
    else:
        assert result.error_code == "serializer_candidate_mutated"
        assert result.generation is None and lifecycle.current_type111 is None


def test_type110_only_malformed_stock_is_still_passed_to_original_serializer():
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    malformed_stock = {"streams": "malformed"}
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": 110, "streamConnectionID": 1101}]},
        malformed_stock, serializer,
    )
    assert result.error_code == "stock_response_streams_invalid"
    assert not result.requested_type111 and result.security_mode == "HONDA_UNKNOWN"
    assert result.serializer_invocations == len(calls) == 1
    assert calls == [malformed_stock] and result.response == malformed_stock
    assert not allocator.reservations and lifecycle.current_type111 is None
    assert type110.active


def test_synthetic_mode_rejects_non_loopback_real_listener_policy():
    lifecycle, _ = _twin()
    allocator = RealListenerAllocator(
        InterfacePolicy(InterfaceKind.SPECIFIC_ADDRESS, "192.0.2.5")
    )
    with pytest.raises(ValueError, match="synthetic_type111_requires_loopback"):
        Type111SetupContract(
            lifecycle, allocator, enable_synthetic_type111_for_tests=True
        )


def test_synthetic_mode_revalidates_listener_policy_before_reservation():
    lifecycle, type110 = _twin()
    allocator = RealListenerAllocator(InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
    contract = Type111SetupContract(
        lifecycle, allocator, enable_synthetic_type111_for_tests=True
    )
    allocator.policy = InterfacePolicy(InterfaceKind.SPECIFIC_ADDRESS, "192.0.2.5")
    calls, serializer = _serializer()

    result = contract.process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]},
        {"streams": [{"type": 110, "dataPort": 41001}]}, serializer,
    )

    assert result.error_code == "synthetic_listener_policy_invalid"
    assert result.security_mode == "SYNTHETIC_TEST_ONLY"
    assert result.serializer_invocations == len(calls) == 1
    assert calls[0] == result.response
    assert not allocator.reservations and lifecycle.current_type111 is None
    assert type110.active


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
    result = _synthetic_contract(lifecycle, DeterministicListenerAllocator()).process(
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
    contract = _synthetic_contract(lifecycle, allocator)
    stock = {"streams": [{"type": 110, "dataPort": 41100, "opaque": {"keep": True}}], "stock": "same"}
    before = repr(a)
    calls, serializer = _serializer()
    result = contract.process(input_request, stock, serializer)
    assert result.serializer_invocations == len(calls) == 1
    assert result.serializer_result == SerializerResult(0xC8, 0)
    assert result.committed
    assert result.response["streams"][0] == stock["streams"][0]
    if any(stream["type"] == 111 for stream in input_request["streams"]):
        assert result.security_mode == "SYNTHETIC_TEST_ONLY"
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
    result = _synthetic_contract(lifecycle, allocator).process(
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
    result = _synthetic_contract(lifecycle, allocator).process(input_request, stock, serializer)
    assert result.error_code
    assert result.serializer_invocations == len(calls) == 1
    assert calls[0] == stock and not allocator.reservations
    assert lifecycle.current_type111 is None


def test_unknown_stream_type_in_type111_request_fails_closed_without_listener():
    lifecycle, _ = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer()
    result = _synthetic_contract(lifecycle, allocator).process(
        {"streams": [{"type": 999, "streamConnectionID": 8}, {"type": 111, "streamConnectionID": 2201}]},
        {"streams": []}, serializer,
    )
    assert result.error_code == "unsupported_stream_type_for_type111_adapter"
    assert result.serializer_invocations == len(calls) == 1
    assert not allocator.reservations and lifecycle.current_type111 is None


@pytest.mark.parametrize("stock", [{"streams": "not-an-array"}, []])
def test_invalid_stock_response_fails_closed_without_listener_and_preserves_stock_serializer_path(stock):
    lifecycle, _ = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer()
    request = {"streams": [{"type": 111, "streamConnectionID": 2201}]}
    result = Type111SetupContract(lifecycle, allocator).process(request, stock, serializer)
    expected = "stock_response_streams_invalid" if isinstance(stock, dict) else "stock_response_must_be_mapping"
    assert result.error_code == expected
    if isinstance(stock, dict):
        assert result.serializer_invocations == len(calls) == 1
        assert calls == [stock]
        assert result.response == stock
    else:
        assert result.serializer_invocations == len(calls) == 1
        assert calls == [stock]
        assert result.response is None
    assert result.security_mode == "TYPE111_DISABLED_AUTHORITY_UNKNOWN"
    assert not allocator.reservations and lifecycle.current_type111 is None


@pytest.mark.parametrize(("setup_request", "error"), [
    ({"streams": [{"type": 111, "streamConnectionID": 11},
                  {"type": 111, "streamConnectionID": 12}]}, "duplicate_type111_request"),
    ({"streams": [{"type": 111.0, "streamConnectionID": 11}]}, "stream_type_must_be_integer"),
])
def test_default_disabled_mode_preserves_specific_malformed_request_errors(setup_request, error):
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    calls, serializer = _serializer()
    stock = {"streams": [{"type": 110, "dataPort": 41001}]}
    result = Type111SetupContract(lifecycle, allocator).process(setup_request, stock, serializer)
    assert result.error_code == error
    expected_mode = (
        "TYPE111_DISABLED_AUTHORITY_UNKNOWN"
        if error == "duplicate_type111_request" else "HONDA_UNKNOWN"
    )
    assert result.security_mode == expected_mode
    assert result.serializer_invocations == len(calls) == 1
    assert calls == [stock]
    assert not allocator.reservations and lifecycle.current_type111 is None
    assert type110.active



def test_disabled_type111_reports_malformed_stream_identity_without_allocating():
    lifecycle, type110 = _twin()
    allocator = DeterministicListenerAllocator()
    stock = {"streams": [{"type": 110, "dataPort": 41001}]}
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 0}]}, stock, serializer
    )
    assert result.error_code == "screen_stream_connection_id_invalid"
    assert result.security_mode == "TYPE111_DISABLED_AUTHORITY_UNKNOWN"
    assert result.serializer_invocations == len(calls) == 1
    assert calls == [stock] and result.response == stock
    assert not allocator.reservations and lifecycle.current_type111 is None
    assert type110.active


def test_malformed_request_precedes_malformed_stock_envelope_diagnostic():
    lifecycle, _type110 = _twin()
    calls, serializer = _serializer()
    result = Type111SetupContract(lifecycle, DeterministicListenerAllocator()).process(
        {"streams": [{"type": 111.0, "streamConnectionID": 2201}]},
        {"streams": "invalid"}, serializer,
    )
    assert result.error_code == "stream_type_must_be_integer"
    assert result.serializer_invocations == len(calls) == 1
    assert result.response == {"streams": "invalid"}

def test_listener_failure_and_mutation_failure_roll_back_exact_generation():
    for allocator, mutate in (
        (DeterministicListenerAllocator(fail_at="bind"), False),
        (DeterministicListenerAllocator(first_port=0), False),
        (DeterministicListenerAllocator(fail_at="closed_before_commit"), False),
        (DeterministicListenerAllocator(), True),
    ):
        lifecycle, a = _twin()
        calls, serializer = _serializer()
        result = _synthetic_contract(lifecycle, allocator).process(
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
    result = _synthetic_contract(lifecycle, allocator).process(
        {"streams": [{"type": 111, "streamConnectionID": 2201}]}, stock, serializer
    )
    assert result.serializer_invocations == len(calls) == 2
    assert result.serializer_result == serializer_result
    assert result.candidate_serializer_result == serializer_result
    assert result.security_mode == "SYNTHETIC_TEST_ONLY"
    assert not result.committed
    assert result.error_code == "type111_candidate_serializer_failed"
    assert result.response == stock
    assert calls[0]["streams"][-1]["type"] == 111 and calls[1] == stock
    assert result.data_port is None and result.listener_id is None
    assert not result.response_appended
    assert result.response["streams"][0] == stock["streams"][0]
    assert lifecycle.current_type111 is None and a.active
    assert allocator.reservations[0].state is ListenerState.CLOSED


def test_new_generation_and_stale_old_listener_cleanup_are_exact_instance_scoped():
    lifecycle, a = _twin()
    allocator = DeterministicListenerAllocator()
    contract = _synthetic_contract(lifecycle, allocator)
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
    result = _synthetic_contract(lifecycle, DeterministicListenerAllocator()).process(
        {"streams": [{"type": 111, "streamConnectionID": raw_id}]}, {"streams": []}, serializer
    )
    assert str(raw_id) not in repr(result)
    assert "key" not in repr(result).lower()
