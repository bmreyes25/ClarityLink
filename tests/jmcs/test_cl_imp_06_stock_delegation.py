from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT),
    str(ROOT / "src/claritylink-jmcs"),
    str(ROOT / "src/claritylink-negotiation"),
    str(ROOT / "src/claritylink-transport"),
    str(ROOT / "src/carplay-session-model"),
]

from claritylink_jmcs.session_transport import ControlRequest, ControlResponse  # noqa: E402
from claritylink_jmcs.receiver import FaultInjector, Receiver  # noqa: E402
from claritylink_jmcs.stock_delegation import (  # noqa: E402
    DelegationError,
    MockStockPrimarySession,
    StockFirstType111Delegator,
)
from claritylink_jmcs.compat.honda.setup import (  # noqa: E402
    EvidenceRequired,
    HondaStaticType110Adapter,
)
from dual_screen_lifecycle import DualScreenLifecycleTwin  # noqa: E402
from legacy_dual_screen_twin import LegacyDualScreenTwin, ScreenRole  # noqa: E402
from project_lifecycle import ChildPhase  # noqa: E402
from demo.cl_imp_11.dual_display_lab import (  # noqa: E402
    MockDelegatedReplayTransport,
    _setup_response_matches_receiver,
)
from type111_setup_contract import (  # noqa: E402
    DeterministicListenerAllocator,
    SecurityMode,
    SerializerResult,
    Type111SetupContract,
)


def make_delegator(*, fail_at=None, synthetic_contract=True, synthetic_delegator=True, no_listener=False):
    twin = LegacyDualScreenTwin(bytes(range(16)),
                                encrypt_block=lambda key, counter: bytes(a ^ b for a, b in zip(key, counter)))
    primary_screen = twin.add_screen(ScreenRole.TYPE110, 1101)
    lifecycle = DualScreenLifecycleTwin(twin)
    allocator = None if no_listener else DeterministicListenerAllocator(fail_at=fail_at)
    contract = Type111SetupContract(
        lifecycle, allocator,
        enable_synthetic_type111_for_tests=synthetic_contract,
    )
    stock_response = {"streams": [{"type": 110, "dataPort": 41001, "opaque": {"stock": True}}],
                      "audio": {"owner": "mock_factory_session"}}
    stock = MockStockPrimarySession(stock_response)
    delegator = StockFirstType111Delegator(
        stock, contract, allow_synthetic_type111_for_tests=synthetic_delegator
    )
    return delegator, stock, primary_screen, lifecycle, allocator, stock_response


def test_type111_delegation_calls_mock_primary_first_and_preserves_its_snapshot():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(42)
    def serializer(response):
        stock.events.append("MOCK_STOCK_SERIALIZER")
        return SerializerResult(0xC8, 0)

    request = {"streams": [
        {"type": 111, "streamConnectionID": 2201},
        {"type": 110, "streamConnectionID": 1101},
    ]}
    result = delegator.handle_setup(42, request, serializer)

    assert stock.events[-2:] == ["MOCK_PRIMARY_SETUP", "MOCK_STOCK_SERIALIZER"]
    assert result.secondary_committed and result.primary_preserved
    assert result.response["streams"][0] == stock_response["streams"][0]
    assert result.response["audio"] == stock_response["audio"]
    assert result.response["streams"][-1]["type"] == 111
    assert primary.active and lifecycle.current_type111.phase is ChildPhase.ACTIVE
    assert allocator.reservations[0].owner_key == lifecycle.current_type111.key
    assert stock.setup_calls == result.transaction.serializer_invocations == 1
    assert result.security_mode == SecurityMode.SYNTHETIC_TEST_ONLY.value


def test_default_delegator_disables_type111_but_preserves_mixed_stock_request():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator(
        synthetic_contract=False, synthetic_delegator=False
    )
    delegator.open(43)
    sent = []

    result = delegator.handle_setup(
        43,
        {"streams": [
            {"type": 111, "streamConnectionID": 2201},
            {"type": 110, "streamConnectionID": 1101},
        ]},
        lambda response: (sent.append(response) or SerializerResult(0xC8, 0)),
    )

    assert result.response == stock_response and sent == [stock_response]
    assert not result.secondary_committed and result.primary_preserved
    assert result.error_code == "type111_authority_unavailable"
    assert result.security_mode == SecurityMode.TYPE111_DISABLED_AUTHORITY_UNKNOWN.value
    assert lifecycle.current_type111 is None and not allocator.reservations
    assert primary.active and stock.active and stock.setup_calls == 1


def test_failed_stock_serializer_is_not_reported_as_a_preserved_primary():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator(
        synthetic_contract=False, synthetic_delegator=False,
    )
    delegator.open(44)
    result = delegator.handle_setup(
        44, {"streams": [{"type": 111, "streamConnectionID": 4401}]},
        lambda _response: SerializerResult(0x1F4, 1),
    )

    assert result.response == stock_response
    assert not result.primary_preserved and not result.secondary_committed
    assert result.error_code == "stock_serializer_failed"
    assert result.transaction.fallback_error_code == "stock_serializer_failed"
    assert lifecycle.current_type111 is None and not allocator.reservations
    assert primary.active and stock.active



def test_missing_transport_allocator_fails_open_to_stock_response():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator(
        synthetic_contract=False, synthetic_delegator=False, no_listener=True
    )
    delegator.open(50)
    calls = []
    result = delegator.handle_setup(
        50, {"streams": [{"type": 111, "streamConnectionID": 5001}]},
        lambda response: (calls.append(response) or SerializerResult(0xC8, 0)),
    )

    assert allocator is None
    assert result.response == stock_response and result.primary_preserved
    assert result.error_code == "type111_authority_unavailable"
    assert result.transaction.serializer_invocations == len(calls) == 1
    assert lifecycle.current_type111 is None
    assert primary.active and stock.active


def test_disabled_type111_lab_transport_returns_stock_only_response():
    delegator, _stock, _primary, _lifecycle, _allocator, stock_response = make_delegator(
        synthetic_contract=False, synthetic_delegator=False
    )
    delegator.open(51)
    request = ControlRequest(
        "SETUP", "/session",
        {"streams": [{"type": 110, "streamConnectionID": 1101},
                    {"type": 111, "streamConnectionID": 5101}]},
        51,
    )

    class ReplayStub:
        responses = []

        def read_request(self, _timeout):
            return request

        def write_response(self, response):
            self.responses.append(response)

        def close(self):
            pass

    replay = ReplayStub()
    transport = MockDelegatedReplayTransport(replay, delegator)
    assert transport.read_request(0) is request
    result = transport.delegation_result
    assert result.error_code == "type111_authority_unavailable"
    assert result.primary_preserved and not result.secondary_committed
    transport.write_response(ControlResponse(200, stock_response, 51))
    assert replay.responses == [ControlResponse(200, stock_response, 51)]


def _type111_setup_request(generation: int) -> ControlRequest:
    return ControlRequest(
        "SETUP", "/session",
        {"streams": [{"type": 110, "streamConnectionID": 1101},
                     {"type": 111, "streamConnectionID": generation + 5100}]},
        generation,
    )


class _ReplayQueue:
    def __init__(self, requests, *, fail_write=False):
        self.requests = list(requests)
        self.responses = []
        self.fail_write = fail_write
        self.closed = False

    def read_request(self, _timeout):
        return self.requests.pop(0)

    def write_response(self, response):
        if self.fail_write:
            raise RuntimeError("injected replay write failure")
        self.responses.append(response)

    def close(self):
        self.closed = True


def test_unwritten_setup_is_rolled_back_before_next_request():
    delegator, _stock, primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(61)
    replay = _ReplayQueue([
        _type111_setup_request(61), ControlRequest("GET", "/info", {}, 61),
    ])
    transport = MockDelegatedReplayTransport(replay, delegator)

    transport.read_request(1)
    assert transport.delegation_result.secondary_committed
    transport.read_request(1)

    assert allocator.reservations[0].state.value == "CLOSED"
    assert lifecycle.current_type111 is None
    assert primary.active and transport.delegation_result is None


def test_setup_response_must_match_delegated_candidate_and_write_failure_rolls_back():
    delegator, _stock, primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(62)
    replay = _ReplayQueue([_type111_setup_request(62)])
    transport = MockDelegatedReplayTransport(
        replay, delegator,
        setup_response_validator=lambda result, response: response.body == result.response,
    )
    transport.read_request(1)
    result = transport.delegation_result
    altered = {**result.response, "streams": [dict(item) for item in result.response["streams"]]}
    altered["streams"][-1]["dataPort"] += 1

    with pytest.raises(RuntimeError, match="does_not_match_committed_streams"):
        transport.write_response(ControlResponse(200, altered, 62))
    assert allocator.reservations[0].state.value == "CLOSED"
    assert lifecycle.current_type111 is None
    assert primary.active and not replay.responses

    delegator, _stock, primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(63)
    replay = _ReplayQueue([_type111_setup_request(63)], fail_write=True)
    transport = MockDelegatedReplayTransport(
        replay, delegator, setup_response_validator=lambda _result, _response: True,
    )
    transport.read_request(1)
    with pytest.raises(RuntimeError, match="injected replay write failure"):
        transport.write_response(ControlResponse(200, {}, 63))
    assert allocator.reservations[0].state.value == "CLOSED"
    assert lifecycle.current_type111 is None
    assert primary.active


def test_transport_close_withdraws_pending_child_for_parent_finalizer():
    delegator, stock, primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(64)
    replay = _ReplayQueue([_type111_setup_request(64)])
    transport = MockDelegatedReplayTransport(replay, delegator)
    transport.read_request(1)
    assert transport.delegation_result.secondary_committed

    transport.close()

    assert replay.closed and primary.active and stock.active
    assert allocator.reservations[0].state.value == "CLOSED"
    assert lifecycle.current_type111 is None


def test_committed_child_rejected_by_outer_flag_is_rolled_back_before_stock_response():
    delegator, _stock, primary, lifecycle, allocator, stock_response = make_delegator(
        synthetic_contract=True, synthetic_delegator=False
    )
    original_process = delegator.secondary.process

    def simulate_contract_flag_mismatch(request, response, serializer, **_kwargs):
        return original_process(
            request, response, serializer,
            allow_synthetic_type111_for_tests=True,
        )

    delegator.secondary.process = simulate_contract_flag_mismatch
    delegator.open(52)
    result = delegator.handle_setup(
        52, {"streams": [{"type": 111, "streamConnectionID": 5201}]},
        lambda _response: SerializerResult(0xC8, 0),
    )

    assert result.response == stock_response and result.primary_preserved
    assert not result.secondary_committed
    assert result.error_code == "type111_not_enabled_by_delegator"
    assert not result.transaction.committed
    assert result.transaction.data_port is None and not result.transaction.response_appended
    assert lifecycle.current_type111 is None and primary.active
    assert allocator.reservations[0].state.value == "CLOSED"


def test_delegator_retries_cleanup_after_contract_cleanup_exception():
    delegator, _stock, primary, lifecycle, allocator, stock_response = make_delegator()
    original_create = lifecycle.create_type111

    def create_with_one_cleanup_failure(stream_connection_id):
        generation = original_create(stream_connection_id)
        original_fail = generation.fail
        attempts = []

        def fail_once():
            attempts.append(True)
            if len(attempts) == 1:
                raise RuntimeError("injected close failure")
            return original_fail()

        generation.fail = fail_once
        return generation

    lifecycle.create_type111 = create_with_one_cleanup_failure
    delegator.open(54)
    result = delegator.handle_setup(
        54, {"streams": [{"type": 111, "streamConnectionID": 5401}]},
        lambda _response: SerializerResult(500, 1),
    )

    assert result.response == stock_response and not result.primary_preserved
    assert not result.secondary_committed
    assert result.error_code == "stock_serializer_failed"
    assert lifecycle.current_type111 is None and primary.active
    assert allocator.reservations[0].state.value == "CLOSED"


def test_parent_cleanup_failure_remains_retryable_without_skipping_primary_loss_handling():
    delegator, stock, primary, lifecycle, _allocator, stock_response = make_delegator()
    delegator.open(55)
    original_destroy = lifecycle.destroy_parent
    attempts = []

    def fail_once():
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError("injected parent cleanup failure")
        return original_destroy()

    lifecycle.destroy_parent = fail_once

    def lose_parent(_response):
        stock.active = False
        return SerializerResult(0xC8, 0)

    result = delegator.handle_setup(
        55, {"streams": [{"type": 110, "streamConnectionID": 1101}]}, lose_parent,
    )

    assert result.response == stock_response and result.primary_preserved
    assert result.error_code == "type111_cleanup_failed"
    assert not stock.active and primary.active and lifecycle.type110.active
    assert delegator._active_generation == 55
    assert delegator.revoke_session(55)
    assert delegator._active_generation is None
    assert not lifecycle.type110.active and lifecycle.parent_destroyed


def test_revoke_rejects_mismatched_primary_identity_without_destroying_current_state():
    delegator, stock, primary, lifecycle, _allocator, _stock_response = make_delegator()
    delegator.open(57)
    stock.generation = 58

    assert not delegator.revoke_session(57)
    assert delegator._active_generation == 57
    assert stock.active and lifecycle.type110.active and primary.active
    assert not lifecycle.parent_destroyed

    stock.generation = 57
    assert delegator.revoke_session(57)
    assert not stock.active and not lifecycle.type110.active


def test_lab_transport_accepts_plain_stock_type110_setup():
    delegator, _stock, _primary, _lifecycle, _allocator, stock_response = make_delegator(
        synthetic_contract=False, synthetic_delegator=False
    )
    delegator.open(53)
    request = ControlRequest(
        "SETUP", "/session",
        {"streams": [{"type": 110, "streamConnectionID": 1101}]}, 53,
    )

    class ReplayStub:
        responses = []

        def read_request(self, _timeout):
            return request

        def write_response(self, response):
            self.responses.append(response)

        def close(self):
            pass

    replay = ReplayStub()
    transport = MockDelegatedReplayTransport(replay, delegator)
    transport.read_request(0)
    result = transport.delegation_result
    assert result.transaction.committed and not result.secondary_committed
    transport.write_response(ControlResponse(200, stock_response, 53))
    assert replay.responses == [ControlResponse(200, stock_response, 53)]


def test_lab_transport_limits_stream_validation_to_matching_setup_response():
    delegator, _stock, _primary, _lifecycle, _allocator, _stock_response = make_delegator()
    delegator.open(56)
    requests = [
        ControlRequest("SETUP", "/session", {
            "streams": [{"type": 111, "streamConnectionID": 5601}],
        }, 56),
        ControlRequest("GET_PARAMETER", "/session", {}, 56),
    ]

    class ReplayStub:
        responses = []

        def read_request(self, _timeout):
            return requests.pop(0)

        def write_response(self, response):
            self.responses.append(response)

        def close(self):
            pass

    replay = ReplayStub()
    expected = []
    transport = MockDelegatedReplayTransport(
        replay, delegator,
        setup_response_validator=lambda result, response: bool(
            expected and response.body == expected[0] == result.response
        ),
    )
    setup = transport.read_request(0)
    setup_response = transport.delegation_result.response
    expected.append(setup_response)
    assert setup.method == "SETUP"
    transport.write_response(ControlResponse(200, setup_response, 56))

    followup = transport.read_request(0)
    assert followup.method == "GET_PARAMETER"
    assert transport.delegation_result is None
    followup_response = ControlResponse(200, {"parameter": "ok"}, 56)
    transport.write_response(followup_response)
    assert replay.responses == [ControlResponse(200, setup_response, 56), followup_response]


def test_transport_close_retries_child_cleanup_after_transient_failure():
    delegator, _stock, _primary, lifecycle, _allocator, _stock_response = make_delegator()
    delegator.open(65)
    replay = _ReplayQueue([_type111_setup_request(65)])
    transport = MockDelegatedReplayTransport(replay, delegator)
    transport.read_request(1)
    child = lifecycle.current_type111
    original_teardown = child.teardown
    attempts = []

    def fail_once():
        attempts.append(True)
        if len(attempts) == 1:
            return False
        return original_teardown()

    child.teardown = fail_once
    with pytest.raises(RuntimeError, match="mock_session_cleanup_failed"):
        transport.close()
    assert not transport._closed and lifecycle.current_type111 is child

    transport.close()
    assert transport._closed and lifecycle.current_type111 is None


def test_committed_delegation_is_rolled_back_when_receiver_returns_type110_only():
    generation = 1
    delegator, _stock, _primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(generation)
    receiver = Receiver(clear_lab=True, faults=FaultInjector("listener_bind"))
    receiver_generation = receiver.start_session()
    assert receiver_generation == generation
    receiver.info_exchanged(generation)
    request = _type111_setup_request(generation)
    replay = _ReplayQueue([request])
    transport = MockDelegatedReplayTransport(
        replay, delegator,
        setup_response_validator=lambda result, response:
            _setup_response_matches_receiver(receiver, result, response),
    )
    transport.read_request(1)
    assert transport.delegation_result.secondary_committed
    fallback = receiver.setup(request.body, generation)
    response = ControlResponse(200, fallback.fields, generation)
    assert [item["type"] for item in response.body["streams"]] == [110]
    assert not _setup_response_matches_receiver(receiver, transport.delegation_result, response)

    with pytest.raises(RuntimeError, match="does_not_match_committed_streams"):
        transport.write_response(response)

    assert lifecycle.current_type111 is None
    assert allocator.reservations[0].state.value == "CLOSED"
    receiver.teardown(generation)


def test_receiver_response_validator_accepts_exact_ports_and_rejects_bad_stream_shapes():
    body = {"streams": [
        {"type": 110, "dataPort": 31001},
        {"type": 111, "dataPort": 31002},
    ]}
    receiver = SimpleNamespace(
        generation=7,
        last_response=SimpleNamespace(fields=body),
        primary=SimpleNamespace(port=31001),
        secondary=SimpleNamespace(port=31002),
    )
    result = SimpleNamespace(
        response={"streams": [{"type": 110}, {"type": 111}]},
        secondary_committed=True,
    )
    response = ControlResponse(200, body, 7)

    assert _setup_response_matches_receiver(receiver, result, response)

    wrong_port = {"streams": [dict(item) for item in body["streams"]]}
    wrong_port["streams"][1]["dataPort"] += 1
    assert not _setup_response_matches_receiver(
        receiver, result, ControlResponse(200, wrong_port, 7),
    )

    duplicate = {"streams": [*body["streams"], dict(body["streams"][1])]}
    receiver.last_response = SimpleNamespace(fields=duplicate)
    assert not _setup_response_matches_receiver(
        receiver, result, ControlResponse(200, duplicate, 7),
    )

    malformed = {"streams": [body["streams"][0], "invalid"]}
    receiver.last_response = SimpleNamespace(fields=malformed)
    assert not _setup_response_matches_receiver(
        receiver, result, ControlResponse(200, malformed, 7),
    )


@pytest.mark.parametrize("response_status", [200, 500])
def test_lab_transport_rolls_back_type111_when_setup_response_is_not_accepted(response_status):
    delegator, _stock, _primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(58)
    request = ControlRequest(
        "SETUP", "/session",
        {"streams": [{"type": 111, "streamConnectionID": 5801}]}, 58,
    )

    class ReplayStub:
        responses = []

        def read_request(self, _timeout):
            return request

        def write_response(self, response):
            self.responses.append(response)

        def close(self):
            pass

    replay = ReplayStub()
    transport = MockDelegatedReplayTransport(replay, delegator)
    transport.read_request(0)
    assert transport.delegation_result.secondary_committed
    rejected_body = stock_response if response_status == 200 else {"error": "rejected"}
    response = ControlResponse(response_status, rejected_body, 58)

    if response_status == 200:
        with pytest.raises(RuntimeError, match="runtime_setup_response_does_not_match_committed_streams"):
            transport.write_response(response)
    else:
        transport.write_response(response)

    assert lifecycle.current_type111 is None
    assert allocator.reservations[0].state.value == "CLOSED"

def test_parent_loss_during_setup_cleans_prior_child_even_when_request_made_no_generation():
    delegator, stock, primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(47)
    first = delegator.handle_setup(
        47, {"streams": [{"type": 111, "streamConnectionID": 4701}]},
        lambda _value: SerializerResult(0xC8, 0),
    )
    assert first.secondary_committed
    original_child = lifecycle.current_type111

    def parent_lost_during_stock_serialization(_value):
        stock.active = False
        return SerializerResult(0xC8, 0)

    result = delegator.handle_setup(
        47, {"streams": [{"type": 110, "streamConnectionID": 1101}]},
        parent_lost_during_stock_serialization,
    )

    assert result.error_code == "session_revoked_during_setup"
    assert result.transaction.generation is None
    assert original_child.phase is ChildPhase.STOPPED
    assert lifecycle.current_type111 is None
    assert allocator.reservations[0].close_count == 1
    assert not primary.active and not stock.active


def test_stale_setup_does_not_destroy_new_parent_opened_during_reentrant_teardown():
    delegator, _old_stock, _old_primary, old_lifecycle, _old_allocator, _response = make_delegator()
    delegator.open(48)
    replacement = make_delegator()
    new_delegator, new_stock, _new_primary, new_lifecycle, _new_allocator, _new_response = replacement

    def replace_parent_during_serialization(_value):
        assert delegator.revoke_session(48)
        delegator.primary = new_stock
        delegator.secondary = new_delegator.secondary
        delegator._allow_synthetic_type111_for_tests = True
        delegator.open(49)
        return SerializerResult(0xC8, 0)

    stale = delegator.handle_setup(
        48, {"streams": [{"type": 111, "streamConnectionID": 4801}]},
        replace_parent_during_serialization,
    )

    assert stale.error_code == "session_revoked_during_setup"
    assert not stale.transaction.committed and stale.transaction.data_port is None
    assert old_lifecycle.parent_destroyed
    assert not new_lifecycle.parent_destroyed and new_stock.active
    current = delegator.handle_setup(
        49, {"streams": [{"type": 111, "streamConnectionID": 4901}]},
        lambda _value: SerializerResult(0xC8, 0),
    )
    assert current.secondary_committed and new_lifecycle.current_type111 is not None


def test_stock_serializer_primary_mutation_is_rejected_and_factory_snapshot_returned():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(52)

    def mutating_serializer(response):
        response["streams"][0]["dataPort"] = 99999
        return SerializerResult(0xC8, 0)

    result = delegator.handle_setup(
        52, {"streams": [{"type": 110, "streamConnectionID": 1101}]},
        mutating_serializer,
    )

    assert result.error_code == "serializer_candidate_mutated"
    assert result.primary_preserved and result.response == stock_response
    assert result.transaction.response == stock_response
    assert "dataPort" in stock_response["streams"][0]
    assert primary.active and stock.active and lifecycle.current_type111 is None
    assert not allocator.reservations

def test_rejected_non_type111_setup_does_not_revoke_an_unrelated_active_child():
    delegator, stock, primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(46)
    first = delegator.handle_setup(
        46, {"streams": [{"type": 111, "streamConnectionID": 4601}]},
        lambda _value: SerializerResult(0xC8, 0),
    )
    assert first.secondary_committed
    original_child = lifecycle.current_type111
    original_process = delegator.secondary.process

    def tamper_stock_first_response(request, stock_response, serializer, **kwargs):
        transaction = original_process(request, stock_response, serializer, **kwargs)
        transaction.response["audio"]["owner"] = "unexpected"
        return transaction

    delegator.secondary.process = tamper_stock_first_response
    rejected = delegator.handle_setup(
        46, {"streams": [{"type": 110, "streamConnectionID": 1101}]},
        lambda _value: SerializerResult(0xC8, 0),
    )

    assert rejected.error_code == "primary_response_changed"
    assert lifecycle.current_type111 is original_child
    assert original_child.phase is ChildPhase.ACTIVE
    assert allocator.reservations[0].state.value == "LISTENING"
    assert primary.active and stock.active
    assert delegator.revoke_session(46)


def test_delegator_does_not_advertise_synthetic_success_without_explicit_lab_opt_in():
    prepared, stock, _primary, lifecycle, allocator, stock_response = make_delegator()
    delegator = StockFirstType111Delegator(stock, prepared.secondary)
    delegator.open(45)
    serialized = []
    result = delegator.handle_setup(
        45, {"streams": [{"type": 111, "streamConnectionID": 4501}]},
        lambda value: (serialized.append(value) or SerializerResult(0xC8, 0)),
    )

    assert result.response == stock_response
    assert not result.secondary_committed and result.primary_preserved
    assert result.error_code == "type111_authority_unavailable"
    assert result.security_mode == SecurityMode.TYPE111_DISABLED_AUTHORITY_UNKNOWN.value
    assert not result.transaction.committed and not result.transaction.response_appended
    assert serialized == [stock_response]
    assert lifecycle.current_type111 is None
    assert not allocator.reservations


def test_malformed_stock_snapshot_is_returned_unchanged_without_serializer_call():
    delegator, stock, primary, lifecycle, allocator, _stock_response = make_delegator(
        synthetic_contract=False, synthetic_delegator=False
    )
    malformed = {"streams": "malformed"}
    stock._response = malformed
    delegator.open(44)
    serializer_calls = []

    result = delegator.handle_setup(
        44, {"streams": [{"type": 111, "streamConnectionID": 4401}]},
        lambda response: (serializer_calls.append(response) or SerializerResult(0xC8, 0)),
    )

    assert result.response == malformed and not result.primary_preserved
    assert result.error_code == "stock_response_streams_invalid"
    assert result.transaction.response == malformed
    assert serializer_calls == [malformed]
    assert result.transaction.serializer_invocations == 1
    assert not result.secondary_committed and not allocator.reservations
    assert lifecycle.current_type111 is None and primary.active and stock.active


@pytest.mark.parametrize("input_request", [
    {"streams": [{"type": 111, "streamConnectionID": 1101}]},
    {"streams": [{"type": 111, "streamConnectionID": 2201},
                  {"type": 111, "streamConnectionID": 2202}]},
    {"streams": [{"type": 111, "streamConnectionID": "bad"}]},
])
def test_bad_secondary_request_returns_exact_stock_response_without_losing_primary(input_request):
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(4)
    serialized = []
    result = delegator.handle_setup(
        4, input_request,
        lambda value: (serialized.append(value) or SerializerResult(0xC8, 0)),
    )

    assert result.response == stock_response
    assert not result.secondary_committed and result.primary_preserved
    assert serialized == [stock_response]
    assert lifecycle.current_type111 is None and not allocator.reservations
    assert stock.active and primary.active and stock.setup_calls == 1


def test_listener_failure_rolls_back_secondary_only_and_keeps_primary_snapshot():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator(fail_at="bind")
    delegator.open(7)
    result = delegator.handle_setup(
        7, {"streams": [{"type": 111, "streamConnectionID": 7001}]},
        lambda _value: SerializerResult(0xC8, 0),
    )

    assert result.response == stock_response
    assert not result.secondary_committed and result.error_code == "listener_reservation_failed"
    assert lifecycle.current_type111 is None and primary.active and stock.active
    assert stock.setup_calls == result.transaction.serializer_invocations == 1
    assert not allocator.reservations


def test_serializer_failure_returns_primary_snapshot_instead_of_candidate_append():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(8)
    calls = []
    result = delegator.handle_setup(
        8, {"streams": [{"type": 111, "streamConnectionID": 8001}]},
        lambda value: (calls.append(value) or SerializerResult(0x1F4, 1)),
    )

    assert not result.secondary_committed and not result.primary_preserved
    assert result.error_code == "stock_serializer_failed"
    assert result.response == stock_response
    assert result.transaction.response == stock_response
    assert result.transaction.data_port is None
    assert not result.transaction.response_appended
    assert calls[0]["streams"][-1]["type"] == 111
    assert calls[1] == stock_response
    assert result.transaction.serializer_invocations == len(calls) == 2
    assert lifecycle.current_type111 is None and primary.active and stock.active
    assert allocator.reservations[0].close_count == 1


def test_failed_type111_serialization_can_fall_back_to_working_stock_type110():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(80)
    calls = []

    def serializer(value):
        calls.append(value)
        if any(item.get("type") == 111 for item in value["streams"]):
            return SerializerResult(500, 1)
        return SerializerResult(0xC8, 0)

    result = delegator.handle_setup(
        80, {"streams": [{"type": 111, "streamConnectionID": 8002}]}, serializer,
    )

    assert result.response == stock_response and result.primary_preserved
    assert not result.secondary_committed
    assert result.error_code == "type111_candidate_serializer_failed"
    assert result.transaction.serializer_result.succeeded
    assert result.transaction.candidate_serializer_result == SerializerResult(500, 1)
    assert result.transaction.serializer_invocations == len(calls) == 2
    assert calls[0]["streams"][-1]["type"] == 111 and calls[1] == stock_response
    assert lifecycle.current_type111 is None and primary.active and stock.active
    assert allocator.reservations[0].close_count == 1


def test_secondary_teardown_and_session_revocation_have_separate_ownership():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(9)
    result = delegator.handle_setup(
        9, {"streams": [{"type": 111, "streamConnectionID": 9001}]},
        lambda _value: SerializerResult(0xC8, 0),
    )
    listener = allocator.reservations[0]
    assert result.secondary_committed

    assert delegator.teardown_secondary(9)
    assert listener.close_count == 1 and lifecycle.current_type111 is None
    assert primary.active and stock.active
    with pytest.raises(DelegationError, match="stale_or_inactive_delegation_generation"):
        delegator.handle_setup(8, {"streams": []}, lambda _value: SerializerResult(0xC8, 0))
    assert delegator.revoke_session(9)
    assert not stock.active
    assert not delegator.revoke_session(9)


@pytest.mark.parametrize("bad_generation", [True, False, 0, -1, "1", None])
def test_generation_fences_reject_boolean_and_other_invalid_aliases(bad_generation):
    delegator, stock, _primary, _lifecycle, _allocator, _stock_response = make_delegator()
    delegator.open(1)

    with pytest.raises(DelegationError, match="stale_or_inactive_delegation_generation"):
        delegator.handle_setup(bad_generation, {"streams": []},
                               lambda _value: SerializerResult(0xC8, 0))
    assert not delegator.teardown_secondary(bad_generation)
    assert not delegator.revoke_session(bad_generation)
    with pytest.raises(DelegationError, match="stale_or_inactive_primary_session"):
        stock.handle_setup(bad_generation, {"streams": []})
    assert not stock.revoke(bad_generation)
    assert stock.active and stock.setup_calls == 0
    assert delegator.revoke_session(1)


def test_generation_revocation_during_serialization_cannot_commit_secondary():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(11)

    def revoke_inside_serializer(_response):
        assert delegator.revoke_session(11)
        return SerializerResult(0xC8, 0)

    result = delegator.handle_setup(
        11, {"streams": [{"type": 111, "streamConnectionID": 11001}]},
        revoke_inside_serializer,
    )

    assert result.response == stock_response
    assert result.error_code == "session_revoked_during_setup"
    assert not result.secondary_committed and result.primary_preserved
    assert not stock.active and lifecycle.current_type111 is None
    assert allocator.reservations[0].close_count == 1
    assert not primary.active


@pytest.mark.parametrize("order", [(110, 111), (111, 110)])
def test_type111_handoff_fixture_accepts_both_orders_without_rewriting_primary(order):
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(20)
    streams = [{"type": kind, "streamConnectionID": 1101 if kind == 110 else 2201}
               for kind in order]
    result = delegator.handle_setup(
        20, {"streams": streams}, lambda _value: SerializerResult(0xC8, 0))

    assert result.secondary_committed and result.primary_preserved
    assert result.response["streams"][0] == stock_response["streams"][0]
    assert result.response["audio"] == stock_response["audio"]
    assert primary.active and stock.active
    assert lifecycle.current_type111.phase is ChildPhase.ACTIVE


def test_inactive_or_wrong_parent_session_cannot_authorize_synthetic_handoff():
    delegator, stock, _primary, _lifecycle, _allocator, _response = make_delegator()
    request = {"streams": [{"type": 111, "streamConnectionID": 2201}]}
    with pytest.raises(DelegationError, match="stale_or_inactive_delegation_generation"):
        delegator.handle_setup(21, request, lambda _value: SerializerResult(0xC8, 0))
    delegator.open(21)
    with pytest.raises(DelegationError, match="stale_or_inactive_delegation_generation"):
        delegator.handle_setup(22, request, lambda _value: SerializerResult(0xC8, 0))
    assert stock.setup_calls == 0


def test_synthetic_mock_authority_does_not_enable_honda_type111_adapter():
    adapter = HondaStaticType110Adapter()
    with pytest.raises(EvidenceRequired, match="honda_type111_setup_dispatch"):
        adapter.parse_known_request(
            {"streams": [{"type": 111, "streamConnectionID": 2201}]},
            generation=28,
        )


@pytest.mark.parametrize("bad_stream", [
    {"type": 111},
    {"type": 111, "streamConnectionID": 0},
    {"type": 111, "streamConnectionID": "opaque"},
])
def test_incomplete_type111_metadata_fails_open_to_exact_mock_stock_response(bad_stream):
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(23)
    sent = []
    result = delegator.handle_setup(
        23, {"streams": [bad_stream]},
        lambda response: (sent.append(response) or SerializerResult(0xC8, 0)))
    assert result.response == stock_response
    assert not result.secondary_committed
    assert sent == [stock_response]
    assert stock.active and primary.active and lifecycle.current_type111 is None
    assert not allocator.reservations


def test_wrong_type_and_primary_connection_id_do_not_create_secondary_stream():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(24)
    wrong_type = delegator.handle_setup(
        24, {"streams": [{"type": 112, "streamConnectionID": 2201}]},
        lambda _value: SerializerResult(0xC8, 0))
    assert wrong_type.response == stock_response and not wrong_type.secondary_committed

    duplicate_id = delegator.handle_setup(
        24, {"streams": [{"type": 111, "streamConnectionID": 1101}]},
        lambda _value: SerializerResult(0xC8, 0))
    assert duplicate_id.response == stock_response
    assert duplicate_id.error_code == "duplicate_stream_connection_id"
    assert stock.active and primary.active and lifecycle.current_type111 is None
    assert not allocator.reservations


def test_duplicate_type111_setup_is_rejected_without_replacing_current_child():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator()
    delegator.open(25)
    request = {"streams": [{"type": 111, "streamConnectionID": 2501}]}
    first = delegator.handle_setup(25, request, lambda _value: SerializerResult(0xC8, 0))
    child = lifecycle.current_type111
    assert first.secondary_committed and child is not None

    second = delegator.handle_setup(25, request, lambda _value: SerializerResult(0xC8, 0))
    assert not second.secondary_committed and second.response == stock_response
    assert lifecycle.current_type111 is child and child.phase is ChildPhase.ACTIVE
    assert primary.active and stock.active and len(allocator.reservations) == 1


def test_secondary_listener_allocation_failure_fails_open_without_touching_primary():
    delegator, stock, primary, lifecycle, allocator, stock_response = make_delegator(fail_at="allocate")
    delegator.open(26)
    result = delegator.handle_setup(
        26, {"streams": [{"type": 111, "streamConnectionID": 2601}]},
        lambda _value: SerializerResult(0xC8, 0))
    assert result.response == stock_response and not result.secondary_committed
    assert result.error_code == "listener_reservation_failed"
    assert stock.active and primary.active and lifecycle.current_type111 is None
    assert not allocator.reservations


def test_synthetic_mode_rejects_missing_listener_allocator_at_construction():
    twin = LegacyDualScreenTwin(bytes(range(16)),
                                encrypt_block=lambda key, counter: bytes(a ^ b for a, b in zip(key, counter)))
    twin.add_screen(ScreenRole.TYPE110, 2901)
    lifecycle = DualScreenLifecycleTwin(twin)
    with pytest.raises(ValueError, match="synthetic_type111_requires_loopback_or_deterministic"):
        Type111SetupContract(
            lifecycle, None, enable_synthetic_type111_for_tests=True
        )


def test_type111_disconnect_and_type110_only_teardown_have_stream_local_ownership():
    delegator, stock, primary, lifecycle, allocator, _stock_response = make_delegator()
    delegator.open(27)
    result = delegator.handle_setup(
        27, {"streams": [{"type": 111, "streamConnectionID": 2701}]},
        lambda _value: SerializerResult(0xC8, 0))
    listener = allocator.reservations[0]
    child = lifecycle.current_type111
    assert result.secondary_committed and child is not None

    assert delegator.teardown_stream(27, 110) is False
    assert lifecycle.current_type111 is child and child.phase is ChildPhase.ACTIVE
    assert listener.close_count == 0 and primary.active and stock.active

    assert delegator.teardown_stream(27, 111) is True
    assert listener.close_count == 1 and lifecycle.current_type111 is None
    assert primary.active and stock.active
    assert delegator.revoke_session(27)
    assert not primary.active and not stock.active
