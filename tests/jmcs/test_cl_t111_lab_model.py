from __future__ import annotations

from copy import deepcopy
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

from claritylink_jmcs.capabilities import CapabilityMode, SecondaryDisplayCapability
from claritylink_jmcs.lab_dual_display import (
    InfoPolicy, LabDualDisplayModel, LabModelError, SyntheticReadiness,
)
from claritylink_jmcs.native_adapter_contract import (
    ChildReadiness, HondaNativeReceiverAdapter, NativeInfoPolicy,
)
from claritylink_jmcs.stock_delegation import (
    MockStockPrimarySession, StockFirstType111Delegator,
)
from type111_setup_contract import (
    DeterministicListenerAllocator, SerializerResult, Type111SetupContract,
)
from claritylink_jmcs.setup import serialize_lab_plist
from dual_screen_lifecycle import DualScreenLifecycleTwin
from legacy_dual_screen_twin import LegacyDualScreenTwin, ScreenRole
from project_lifecycle import ChildPhase


STOCK_INFO = {
    "sourceVersion": "synthetic-fixture",
    "features": 17,
    "displays": [{"type": 110,
                  "uuid": "b7e6c5a0-1111-4000-8000-000000000001",
                  "features": 10}],
    "audio": {"owner": "mock_factory_session", "unchanged": True},
}
STOCK_SETUP = {
    "streams": [{"type": 110, "dataPort": 41001, "opaque": {"stock": True}}],
    "audio": {"owner": "mock_factory_session", "opaque": b"factory-value"},
}


def make_model(*, fail_at: str | None = None, readiness: SyntheticReadiness | None = None):
    twin = LegacyDualScreenTwin(
        bytes(16), encrypt_block=lambda key, counter: bytes(a ^ b for a, b in zip(key, counter))
    )
    primary_screen = twin.add_screen(ScreenRole.TYPE110, 1101)
    lifecycle = DualScreenLifecycleTwin(twin)
    allocator = DeterministicListenerAllocator(fail_at=fail_at)
    child_contract = Type111SetupContract(lifecycle, allocator)
    stock = MockStockPrimarySession(STOCK_SETUP)
    delegator = StockFirstType111Delegator(stock, child_contract)
    capability = SecondaryDisplayCapability.synthetic_lab(
        main_uuid="b7e6c5a0-1111-4000-8000-000000000001",
        secondary_uuid="b7e6c5a0-2222-4000-8000-000000000002",
    )
    model = LabDualDisplayModel(
        delegator, STOCK_INFO, STOCK_SETUP,
        secondary_capability=capability,
        readiness=readiness or SyntheticReadiness(True, True, True),
    )
    parent_identity = object()
    return model, stock, primary_screen, lifecycle, allocator, parent_identity


def successful_serializer(captured: list[dict] | None = None):
    def serialize(fields):
        if captured is not None:
            captured.append(deepcopy(dict(fields)))
        serialize_lab_plist(fields)
        return SerializerResult(0xC8, 0)
    return serialize


def open_model(*, fail_at: str | None = None, readiness: SyntheticReadiness | None = None):
    values = make_model(fail_at=fail_at, readiness=readiness)
    model, _stock, _screen, _life, _allocator, identity = values
    model.open(identity, 1)
    return values


def request(*orders: tuple[int, int]) -> dict:
    return {"streams": [
        {"type": kind, "streamConnectionID": connection_id}
        for kind, connection_id in orders
    ]}


def test_info_is_primary_only_by_default_without_child_allocations_or_mutation():
    model, stock, _screen, lifecycle, allocator, parent = open_model()
    original_info = deepcopy(STOCK_INFO)
    result = model.get_info(parent, 1)
    assert result.fields == original_info
    assert not result.type111_candidate_present and result.evidence == "MODEL_ONLY"
    assert [display["type"] for display in result.fields["displays"]] == [110]
    assert stock.setup_calls == 0 and allocator.reservations == []
    assert lifecycle.current_type111 is None and STOCK_INFO == original_info
    assert model.close_parent(parent, 1)


@pytest.mark.parametrize("readiness", [
    SyntheticReadiness(False, True, True),
    SyntheticReadiness(True, False, True),
    SyntheticReadiness(True, True, False),
])
def test_each_missing_readiness_condition_withholds_secondary_candidate(readiness):
    model, _stock, _screen, lifecycle, allocator, parent = open_model(readiness=readiness)
    result = model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    assert not result.type111_candidate_present
    assert [display["type"] for display in result.fields["displays"]] == [110]
    assert lifecycle.current_type111 is None and allocator.reservations == []
    model.close_parent(parent, 1)


def test_ready_model_candidate_is_separate_and_preserves_stock_info():
    model, _stock, _screen, lifecycle, allocator, parent = open_model()
    before = deepcopy(STOCK_INFO)
    result = model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    assert result.type111_candidate_present and result.evidence == "MODEL_ONLY"
    assert [display["type"] for display in result.fields["displays"]] == [110, 111]
    assert result.fields["displays"][0] == before["displays"][0]
    assert result.fields["audio"] == before["audio"]
    assert result.fields["displays"][1]["uuid"] != result.fields["displays"][0]["uuid"]
    assert STOCK_INFO == before and lifecycle.current_type111 is None
    assert allocator.reservations == []  # Capability candidate is not a live child.
    model.close_parent(parent, 1)


@pytest.mark.parametrize("order", [
    ((110, 1101), (111, 2201)),
    ((111, 2201), (110, 1101)),
])
def test_setup_orders_create_one_listener_owned_child_after_stock_setup(order):
    model, stock, _screen, lifecycle, allocator, parent = open_model()
    info = model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    assert info.type111_candidate_present
    captured = []
    result = model.handle_setup(parent, 1, request(*order), successful_serializer(captured))
    child = lifecycle.current_type111
    assert result.child_committed and result.stock_parent_preserved
    assert result.response["streams"][0] == STOCK_SETUP["streams"][0]
    assert result.response["audio"] == STOCK_SETUP["audio"]
    assert result.response["streams"][-1]["type"] == 111
    assert result.serializer_invocations == stock.setup_calls == 1
    assert len(allocator.reservations) == 1
    assert allocator.reservations[0].state.value == "LISTENING"
    assert child is not None and child.phase is ChildPhase.ACTIVE
    assert allocator.reservations[0].owner_key == child.key
    assert captured[-1] == result.response
    assert model.close_parent(parent, 1)
    assert allocator.reservations[0].close_count == 1
    assert lifecycle.current_type111 is None and not stock.active


def test_listener_failure_after_candidate_advertisement_withdraws_only_child():
    model, stock, primary_screen, lifecycle, allocator, parent = open_model()
    assert model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY).type111_candidate_present
    allocator.fail_at = "bind"  # Failure between candidate negotiation and SETUP commit.
    captured = []
    result = model.handle_setup(
        parent, 1, request((110, 1101), (111, 2201)), successful_serializer(captured)
    )
    assert not result.child_committed and result.stock_parent_preserved
    assert result.error_code == "listener_reservation_failed"
    assert result.response == STOCK_SETUP and captured == [STOCK_SETUP]
    assert stock.active and primary_screen.active and lifecycle.current_type111 is None
    assert allocator.reservations == []
    assert model.close_parent(parent, 1)


def test_unready_type111_setup_uses_exact_stock_response_and_does_not_close_parent():
    readiness = SyntheticReadiness(True, False, True)
    model, stock, primary_screen, lifecycle, allocator, parent = open_model(readiness=readiness)
    info = model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    assert not info.type111_candidate_present
    captured = []
    result = model.handle_setup(
        parent, 1, request((110, 1101), (111, 2201)), successful_serializer(captured)
    )
    assert result.response == STOCK_SETUP and captured == [STOCK_SETUP]
    assert result.error_code == "type111_not_advertised_or_ready"
    assert not result.child_committed and result.stock_parent_preserved
    assert stock.active and primary_screen.active and lifecycle.current_type111 is None
    assert allocator.reservations == [] and stock.setup_calls == 1
    assert model.close_parent(parent, 1)


def test_type110_only_setup_is_stock_equivalent_and_has_no_type111_state():
    model, stock, primary_screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1)
    captured = []
    result = model.handle_setup(
        parent, 1, request((110, 1101)), successful_serializer(captured)
    )
    assert result.response == STOCK_SETUP and captured == [STOCK_SETUP]
    assert serialize_lab_plist(result.response) == serialize_lab_plist(STOCK_SETUP)
    assert not result.child_committed and result.stock_parent_preserved
    assert stock.setup_calls == 1 and primary_screen.active
    assert lifecycle.current_type111 is None and allocator.reservations == []
    model.close_parent(parent, 1)


def test_missing_parent_and_wrong_identity_are_rejected_before_stock_setup():
    model, stock, _screen, _lifecycle, _allocator, parent = make_model()
    with pytest.raises(LabModelError, match="parent_session_identity_or_generation_mismatch"):
        model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    model.open(parent, 1)
    with pytest.raises(LabModelError, match="parent_session_identity_or_generation_mismatch"):
        model.get_info(object(), 1, policy=InfoPolicy.MODEL_ONLY)
    with pytest.raises(LabModelError, match="parent_session_identity_or_generation_mismatch"):
        model.handle_setup(object(), 1, request((111, 2201)), successful_serializer())
    assert stock.setup_calls == 0
    model.close_parent(parent, 1)


@pytest.mark.parametrize("bad_request", [
    {"streams": "not-an-array"},
    {"streams": [{"type": 111, "streamConnectionID": 2201}] * 17},
    {"streams": ["bad-entry"]},
])
def test_invalid_or_oversized_setup_rolls_back_to_stock(bad_request):
    model, stock, primary_screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    captured = []
    result = model.handle_setup(parent, 1, bad_request, successful_serializer(captured))
    assert result.response == STOCK_SETUP and captured == [STOCK_SETUP]
    assert not result.child_committed and result.stock_parent_preserved
    assert stock.active and primary_screen.active and lifecycle.current_type111 is None
    assert allocator.reservations == []
    model.close_parent(parent, 1)


def test_setup_already_in_progress_declines_without_claiming_a_stock_response():
    model, stock, _screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    model.delegator._setup_in_progress = True
    captured = []
    result = model.handle_setup(
        parent, 1, request((110, 1101)), successful_serializer(captured)
    )
    assert result.response == {}
    assert result.error_code == "setup_already_in_progress"
    assert result.serializer_invocations == 0 and captured == []
    assert stock.setup_calls == 0 and result.stock_parent_preserved
    assert lifecycle.current_type111 is None and allocator.reservations == []
    model.delegator._setup_in_progress = False
    model.close_parent(parent, 1)


def test_stock_owner_response_remains_authoritative_when_fixture_differs():
    model, stock, _screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    model._stock_setup_response = {"fixture": "deliberately-different"}
    captured = []
    result = model.handle_setup(
        parent, 1, {"malformed": True}, successful_serializer(captured)
    )
    assert result.response == STOCK_SETUP
    assert captured == [STOCK_SETUP]
    assert result.error_code == "stock_fixture_mismatch"
    assert stock.setup_calls == result.serializer_invocations == 1
    assert stock.active and lifecycle.current_type111 is None
    assert allocator.reservations == []
    model.close_parent(parent, 1)


def test_setup_serializer_failure_releases_child_and_returns_stock_snapshot():
    model, stock, primary_screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    calls = []
    def failed_serializer(fields):
        calls.append(deepcopy(dict(fields)))
        return SerializerResult(500, 1)
    result = model.handle_setup(parent, 1, request((111, 2201)), failed_serializer)
    assert result.response == STOCK_SETUP and not result.child_committed
    assert result.error_code == "stock_serializer_failed"
    assert len(calls) == 1 and calls[0]["streams"][-1]["type"] == 111
    assert allocator.reservations[0].close_count == 1
    assert lifecycle.current_type111 is None and stock.active and primary_screen.active
    assert model.close_parent(parent, 1)


def test_disconnect_during_serialization_cannot_commit_child():
    model, stock, primary_screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    def disconnect_during_prepare(_fields):
        assert model.close_parent(parent, 1)
        return SerializerResult(0xC8, 0)
    result = model.handle_setup(parent, 1, request((111, 2201)), disconnect_during_prepare)
    assert not result.child_committed
    assert result.error_code == "session_revoked_during_setup"
    assert result.response == STOCK_SETUP
    assert not stock.active and not primary_screen.active
    assert lifecycle.current_type111 is None and allocator.reservations[0].close_count == 1


def test_duplicate_setup_preserves_existing_child_and_rejects_second_child():
    model, stock, primary_screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    first = model.handle_setup(parent, 1, request((111, 2201)), successful_serializer())
    child = lifecycle.current_type111
    second = model.handle_setup(parent, 1, request((111, 2201)), successful_serializer())
    assert first.child_committed and child is not None
    assert not second.child_committed and second.response == STOCK_SETUP
    assert lifecycle.current_type111 is child and child.phase is ChildPhase.ACTIVE
    assert stock.active and primary_screen.active and len(allocator.reservations) == 1
    model.close_parent(parent, 1)


def test_child_teardown_is_independent_and_parent_teardown_cleans_all_resources():
    model, stock, primary_screen, lifecycle, allocator, parent = open_model()
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    assert model.handle_setup(parent, 1, request((111, 2201)), successful_serializer()).child_committed
    reservation = allocator.reservations[0]
    assert model.teardown_type111(parent, 1)
    assert reservation.close_count == 1 and lifecycle.current_type111 is None
    assert stock.active and primary_screen.active
    model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)
    assert model.handle_setup(parent, 1, request((111, 2202)), successful_serializer()).child_committed
    second_reservation = allocator.reservations[1]
    assert model.close_parent(parent, 1)
    assert second_reservation.close_count == 1
    assert lifecycle.current_type111 is None and not stock.active and not primary_screen.active
    with pytest.raises(LabModelError, match="parent_session_identity_or_generation_mismatch"):
        model.get_info(parent, 1, policy=InfoPolicy.MODEL_ONLY)


def test_reconnect_uses_new_parent_generation_and_rejects_stale_old_events():
    first, _stock1, _screen1, _life1, _allocator1, identity = open_model()
    first.get_info(identity, 1, policy=InfoPolicy.MODEL_ONLY)
    assert first.handle_setup(identity, 1, request((111, 2201)), successful_serializer()).child_committed
    assert first.close_parent(identity, 1)
    second, stock2, _screen2, lifecycle2, allocator2, identity2 = make_model()
    # The test models reconnect with a new parent-owned identity and generation.
    identity2 = identity
    second.open(identity2, 2)
    second.get_info(identity2, 2, policy=InfoPolicy.MODEL_ONLY)
    with pytest.raises(LabModelError, match="parent_session_identity_or_generation_mismatch"):
        first.handle_setup(identity, 1, request((111, 2202)), successful_serializer())
    current = second.handle_setup(
        identity2, 2, request((111, 2203)), successful_serializer()
    )
    assert current.child_committed and stock2.active
    assert lifecycle2.current_type111 is not None
    assert allocator2.reservations[0].generation == lifecycle2.current_type111.generation
    second.close_parent(identity2, 2)


def test_native_adapter_contract_is_only_a_protocol_and_never_honda_readiness():
    assert getattr(HondaNativeReceiverAdapter, "_is_protocol", False)
    assert NativeInfoPolicy.DISABLED.value == "disabled"
    readiness = ChildReadiness(False, False, False)
    assert readiness.ready is False
    assert all(value is False for value in (
        readiness.listener_ready, readiness.independent_security_ready,
        readiness.screen_association_ready,
    ))
