"""Synthetic tests for the fail-closed factory integration contract (CL-FACTORY-01 M6-C).

Offline only. Assert UNKNOWN->deny, synthetic-never-promotes, safe_for_honda guard,
and that safe-direction actions always succeed. No vehicle, no I/O.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-honda"))

import pytest
import factory_integration_contract as fic


def _all_granted(tier=fic.EvidenceTier.FACTORY_PROVEN):
    g = fic.Support.GRANTED
    return fic.FactoryCapability(
        receiver_admits_secondary_stream=g,
        navigation_presentation_permitted=g,
        frame_sink_contract=g,
        display_geometry_known=g,
        page_ownership_lease=g,
        warning_withdrawal_contract=g,
        restoration_contract=g,
        evidence_tier=tier,
    )


def test_default_capability_is_unknown_not_denied():
    cap = fic.FactoryCapability()
    # "no supported handoff found" == UNKNOWN, which is distinct from DENIED (impossible).
    assert cap.receiver_admits_secondary_stream is fic.Support.UNKNOWN
    assert cap.evidence_tier is fic.EvidenceTier.UNKNOWN
    assert cap.granted("receiver_admits_secondary_stream") is False


def test_default_contract_denies_every_forward_gate():
    c = fic.default_fail_closed_contract()
    assert c.safe_for_honda() is False
    assert c.admit_receiver_session(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN).reason_code == fic.R_FACTORY_CONTRACT_UNKNOWN
    assert not c.permit_navigation_presentation()
    d = c.submit_frame_to_factory(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN)
    assert d.allowed is False and d.fail_closed is True


@pytest.mark.parametrize("tier", [fic.EvidenceTier.UNKNOWN, fic.EvidenceTier.SYNTHETIC, fic.EvidenceTier.LAB])
def test_non_factory_evidence_never_admits_even_with_granted_capability(tier):
    c = fic.FactoryIntegrationContract(_all_granted(tier=tier))
    d = c.admit_receiver_session(evidence_tier=tier)
    assert d.allowed is False
    assert d.reason_code == fic.R_SYNTHETIC_NOT_PROMOTABLE
    assert c.admitted is False


def test_factory_proven_admits_and_permits_but_frame_blocked_by_safe_guard():
    c = fic.FactoryIntegrationContract(_all_granted())
    assert c.admit_receiver_session(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN).allowed is True
    assert c.permit_navigation_presentation().allowed is True
    assert c.permitted is True
    # Even fully granted + factory-proven, frames to the factory sink are blocked:
    # safe_for_honda() is False, so nothing reaches the real cluster.
    d = c.submit_frame_to_factory(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN)
    assert d.allowed is False
    assert d.reason_code == fic.R_SAFE_FOR_HONDA_FALSE


def test_permit_requires_admission_first():
    c = fic.FactoryIntegrationContract(_all_granted())
    assert c.permit_navigation_presentation().reason_code == fic.R_NOT_ADMITTED


def test_safe_direction_actions_always_succeed_and_withdraw():
    c = fic.FactoryIntegrationContract(_all_granted())
    c.admit_receiver_session(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN)
    c.permit_navigation_presentation()
    assert c.permitted is True
    assert c.withdraw_for_warning().allowed is True
    assert c.permitted is False  # warning withdrawal forces yield
    for action in (c.on_source_death, c.on_host_death, c.revoke, c.cleanup, c.restore_factory):
        assert action().allowed is True
    assert c.admitted is False and c.permitted is False


def test_restore_factory_is_always_available():
    c = fic.default_fail_closed_contract()
    assert c.restore_factory().allowed is True


def test_contract_exposes_no_fabricated_session_token():
    # The contract must not invent a transaction number / caller token.
    c = fic.FactoryIntegrationContract(_all_granted())
    c.admit_receiver_session(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN)
    for attr in ("token", "session_token", "caller_token", "transaction", "txn", "txn_id"):
        assert not hasattr(c, attr)
