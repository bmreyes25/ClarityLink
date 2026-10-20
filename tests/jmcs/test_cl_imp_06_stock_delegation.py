from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "src/claritylink-jmcs"),
    str(ROOT / "src/claritylink-negotiation"),
    str(ROOT / "src/claritylink-transport"),
    str(ROOT / "src/carplay-session-model"),
]

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
from type111_setup_contract import (  # noqa: E402
    DeterministicListenerAllocator,
    SerializerResult,
    Type111SetupContract,
)


def make_delegator(*, fail_at=None):
    twin = LegacyDualScreenTwin(bytes(range(16)),
                                encrypt_block=lambda key, counter: bytes(a ^ b for a, b in zip(key, counter)))
    primary_screen = twin.add_screen(ScreenRole.TYPE110, 1101)
    lifecycle = DualScreenLifecycleTwin(twin)
    allocator = DeterministicListenerAllocator(fail_at=fail_at)
    contract = Type111SetupContract(lifecycle, allocator)
    stock_response = {"streams": [{"type": 110, "dataPort": 41001, "opaque": {"stock": True}}],
                      "audio": {"owner": "mock_factory_session"}}
    stock = MockStockPrimarySession(stock_response)
    delegator = StockFirstType111Delegator(stock, contract)
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
    result = delegator.handle_setup(
        8, {"streams": [{"type": 111, "streamConnectionID": 8001}]},
        lambda _value: SerializerResult(0x1F4, 1),
    )

    assert not result.secondary_committed and result.primary_preserved
    assert result.response == stock_response
    assert result.transaction.response["streams"][-1]["type"] == 111
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


def test_missing_transport_allocator_fails_open_to_stock_response():
    delegator, stock, primary, lifecycle, _allocator, stock_response = make_delegator()
    delegator.secondary = Type111SetupContract(lifecycle, None)
    delegator.open(29)
    result = delegator.handle_setup(
        29, {"streams": [{"type": 111, "streamConnectionID": 2901}]},
        lambda _value: SerializerResult(0xC8, 0))
    assert result.response == stock_response
    assert not result.secondary_committed and result.primary_preserved
    assert lifecycle.current_type111 is None and primary.active and stock.active


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
