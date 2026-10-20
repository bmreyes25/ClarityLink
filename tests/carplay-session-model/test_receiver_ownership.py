"""Synthetic ownership constraints; no iPhone, Honda, socket or ADB access."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "src/carplay-session-model/receiver_ownership.py"
spec = importlib.util.spec_from_file_location("receiver_ownership", SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
OwnershipClaim = module.OwnershipClaim
Topology = module.Topology
ModelLifecycle = module.ModelLifecycle
validate_claim = module.validate_claim


def claim(kind=Topology.DELEGATED_MEDIA_ENDPOINT, **changes):
    baseline = OwnershipClaim(
        topology=kind,
        secondary_owner="ClarityLink",
        secondary_session="stock",
        secondary_generation=1,
        delegation_contract_proven=True,
        secondary_security_proven=True,
        setup_valid=True,
        type111_requested=True,
        secondary_listener_ready=True,
    )
    return replace(baseline, **changes)


@pytest.mark.parametrize("change,reason", [
    ({"usb_owners": frozenset({"Honda", "ClarityLink"})}, "conflicting_usb_owner"),
    ({"auth_owners": frozenset({"Honda", "ClarityLink"})}, "conflicting_accessory_identity"),
    ({"control_owners": frozenset({"Honda", "ClarityLink"})}, "duplicate_control_owner"),
    ({"primary_owners": frozenset({"ClarityLink"})}, "stock_type110_not_preserved"),
    ({"stock_type110_active": False}, "stock_type110_not_preserved"),
    ({"secondary_session": "other"}, "secondary_session_mismatch"),
    ({"secondary_generation": 2}, "stale_session_generation"),
    ({"delegation_contract_proven": False}, "delegation_unproven"),
    ({"secondary_security_proven": False}, "secondary_security_unproven"),
    ({"setup_valid": False}, "malformed_or_unsupported_setup"),
    ({"secondary_listener_ready": False}, "secondary_listener_unavailable"),
])
def test_shared_endpoint_rejects_unsupported_claims(change, reason):
    assert reason in validate_claim(claim(**change))


def test_single_receiver_two_streams_is_model_only_when_consistent():
    assert validate_claim(claim(Topology.ONE_RECEIVER_TWO_STREAMS, secondary_owner="Honda")) == ()


def test_one_receiver_cannot_assign_second_stream_to_other_owner_without_contract():
    assert "single_receiver_ownership_mismatch" in validate_claim(claim(Topology.ONE_RECEIVER_TWO_STREAMS))


def test_two_receivers_shared_session_requires_delegation():
    assert "delegation_unproven" in validate_claim(
        claim(Topology.TWO_RECEIVERS_SHARED_SESSION, delegation_contract_proven=False)
    )


def test_two_independent_sessions_require_distinct_identity_and_permission():
    two = claim(Topology.TWO_RECEIVERS_TWO_SESSIONS, secondary_session="second",
                secondary_generation=1, auth_owners=frozenset({"Honda", "ClarityLink"}),
                control_owners=frozenset({"Honda", "ClarityLink"}),
                iap2_owners=frozenset({"Honda", "ClarityLink"}))
    assert "second_session_unproven" in validate_claim(two)
    assert "iap2_multiplex_unproven" in validate_claim(two)
    assert validate_claim(replace(two, distinct_authorized_identity=True,
                                  second_session_permission_proven=True,
                                  iap2_multiplex_contract_proven=True)) == ()


def test_independent_wireless_link_needs_discovery_and_session_permission():
    two = claim(Topology.TWO_RECEIVERS_TWO_SESSIONS, secondary_session="second",
                auth_owners=frozenset({"Honda", "ClarityLink"}),
                control_owners=frozenset({"Honda", "ClarityLink"}),
                iap2_owners=frozenset({"Honda", "ClarityLink"}),
                secondary_transport="independent-wireless",
                distinct_authorized_identity=True, second_session_permission_proven=True)
    assert "wireless_link_unproven" in validate_claim(two)
    assert validate_claim(replace(two, wireless_discovery_proven=True)) == ()


def test_duplicate_independent_session_id_rejected():
    assert "duplicate_session_identity" in validate_claim(
        claim(Topology.TWO_RECEIVERS_TWO_SESSIONS, distinct_authorized_identity=True,
              second_session_permission_proven=True)
    )


def test_independent_session_claim_requires_claritylink_auth_and_control_owner():
    empty = claim(Topology.TWO_RECEIVERS_TWO_SESSIONS, secondary_session="second",
                  distinct_authorized_identity=True, second_session_permission_proven=True)
    assert "independent_owner_mismatch" in validate_claim(empty)


def test_metadata_subscriber_needs_content_and_no_apk_admission():
    subscriber = claim(Topology.METADATA_SUBSCRIBER, type111_requested=False)
    assert "metadata_subscriber_unproven" in validate_claim(subscriber)
    assert validate_claim(replace(subscriber, external_content_contract_proven=True,
                                  no_apk_admission_proven=True)) == ()


def test_independent_companion_is_not_stock_route_without_data_path():
    companion = claim(Topology.INDEPENDENT_COMPANION, type111_requested=False)
    assert "independent_data_path_unproven" in validate_claim(companion)


@pytest.mark.parametrize("order", [(110, 111), (111, 110)])
def test_synthetic_stream_order_does_not_change_ownership(order):
    state = ModelLifecycle(primary_active=False)
    early_secondary_rejected = False
    for stream in order:
        if stream == 110:
            assert state.start_primary()
        else:
            started = state.start_secondary(setup_valid=True, security_ready=True, listener_ready=True)
            early_secondary_rejected = not started
    assert early_secondary_rejected == (order[0] == 111)
    assert state.primary_active
    assert state.secondary_active == (order[-1] == 111)
    if early_secondary_rejected:
        assert state.start_secondary(setup_valid=True, security_ready=True, listener_ready=True)
    assert validate_claim(claim()) == ()


def test_secondary_disconnect_does_not_stop_primary():
    state = ModelLifecycle()
    assert state.start_secondary(setup_valid=True, security_ready=True, listener_ready=True)
    state.stop_secondary()
    state.stop_secondary()
    assert state.primary_active and not state.secondary_active
    assert state.closed == ["listener", "security"]


def test_primary_disconnect_releases_secondary_resources():
    state = ModelLifecycle()
    assert state.start_secondary(setup_valid=True, security_ready=True, listener_ready=True)
    state.stop_primary()
    assert not state.primary_active and not state.secondary_active
    assert state.resources == []


@pytest.mark.parametrize("setup,security,listener,closed", [
    (False, True, True, []),
    (True, False, True, []),
    (True, True, False, ["security"]),
])
def test_partial_initialization_cleans_only_acquired_resources(setup, security, listener, closed):
    state = ModelLifecycle()
    assert not state.start_secondary(setup_valid=setup, security_ready=security,
                                     listener_ready=listener)
    assert state.resources == [] and state.closed == closed and state.primary_active


def test_secondary_cannot_restart_after_primary_disconnect():
    state = ModelLifecycle()
    state.stop_primary()
    assert not state.start_secondary(setup_valid=True, security_ready=True, listener_ready=True)


@pytest.mark.parametrize("change,reason", [
    ({"topology": "unknown"}, "unsupported_topology"),
    ({"primary_session": ""}, "invalid_primary_session_identity"),
    ({"secondary_session": ""}, "invalid_secondary_session_identity"),
    ({"primary_generation": True}, "invalid_generation"),
    ({"secondary_generation": False}, "invalid_generation"),
])
def test_runtime_invalid_claim_values_fail_closed(change, reason):
    assert reason in validate_claim(claim(**change))
