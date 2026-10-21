"""Fail-closed factory integration admission contract (CL-FACTORY-01 / M6-C).

Original, offline, synthetic-only model. It composes the gates a hypothetical
ClarityLink<->factory integration would require and defaults every unknown
Honda-side fact to deny. It performs NO I/O, holds NO secrets, invents NO
transaction numbers or caller tokens, and never enables real integration.

Design rules (do not relax):
  * Tri-state ``Support`` is ``UNKNOWN`` by default. ``UNKNOWN`` means "no
    supported handoff has been established" -- it is NOT a proof of
    impossibility and NOT a grant. Fail-closed: only ``GRANTED`` permits.
  * Only ``EvidenceTier.FACTORY_PROVEN`` can satisfy an admission gate.
    ``SYNTHETIC``/``LAB`` evidence can never enable real integration.
  * ``safe_for_honda()`` is always ``False`` and gates every factory-facing
    action. This guard is not configurable here.
  * The "forward" gates (admit/permit/submit-to-factory) fail closed; the
    "safe-direction" actions (withdraw/source-death/host-death/revoke/cleanup/
    restore) always succeed, because removing custom content is always allowed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class Support(str, Enum):
    """Tri-state knowledge of a factory-side capability."""
    UNKNOWN = "UNKNOWN"   # no supported handoff established (NOT impossible, NOT granted)
    DENIED = "DENIED"     # positively established as not permitted
    GRANTED = "GRANTED"   # positively established as permitted (requires FACTORY_PROVEN evidence)


class EvidenceTier(str, Enum):
    UNKNOWN = "UNKNOWN"
    SYNTHETIC = "SYNTHETIC"          # offline lab fixtures; never promotable
    LAB = "LAB"                      # authorized bench hardware; still not factory
    FACTORY_PROVEN = "FACTORY_PROVEN"  # evidence from the actual factory contract


# Reason codes (stable, machine-checkable).
R_FACTORY_CONTRACT_UNKNOWN = "FACTORY_CONTRACT_UNKNOWN"
R_SYNTHETIC_NOT_PROMOTABLE = "SYNTHETIC_NOT_PROMOTABLE"
R_NOT_ADMITTED = "NOT_ADMITTED"
R_PRESENTATION_NOT_PERMITTED = "PRESENTATION_NOT_PERMITTED"
R_GEOMETRY_UNKNOWN = "GEOMETRY_UNKNOWN"
R_FRAME_SINK_UNKNOWN = "FRAME_SINK_UNKNOWN"
R_SAFE_FOR_HONDA_FALSE = "SAFE_FOR_HONDA_FALSE"
R_OK_SAFE_DIRECTION = "OK_SAFE_DIRECTION"
R_GRANTED = "GRANTED"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason_code: str
    fail_closed: bool = True

    def __bool__(self) -> bool:  # convenience: ``if decision:``
        return self.allowed


def _deny(code: str) -> Decision:
    return Decision(allowed=False, reason_code=code, fail_closed=True)


def _grant(code: str = R_GRANTED) -> Decision:
    return Decision(allowed=True, reason_code=code, fail_closed=False)


@dataclass(frozen=True)
class FactoryCapability:
    """What is (not) known about the factory side. Everything defaults UNKNOWN."""
    receiver_admits_secondary_stream: Support = Support.UNKNOWN
    navigation_presentation_permitted: Support = Support.UNKNOWN
    frame_sink_contract: Support = Support.UNKNOWN
    display_geometry_known: Support = Support.UNKNOWN
    page_ownership_lease: Support = Support.UNKNOWN
    warning_withdrawal_contract: Support = Support.UNKNOWN
    restoration_contract: Support = Support.UNKNOWN
    # The maximum evidence tier backing any GRANTED fact above.
    evidence_tier: EvidenceTier = EvidenceTier.UNKNOWN

    def granted(self, name: str) -> bool:
        return getattr(self, name) is Support.GRANTED and self.evidence_tier is EvidenceTier.FACTORY_PROVEN


class FactoryIntegrationContract:
    """Composes admission/presentation/frame gates; fail-closed throughout.

    All state is in-memory and synthetic. ``admitted``/``permitted`` can only
    become True through FACTORY_PROVEN capability, which this campaign does not
    possess; in practice every forward gate denies with a stable reason code.
    """

    def __init__(self, capability: FactoryCapability | None = None) -> None:
        self._cap = capability or FactoryCapability()
        self._admitted = False
        self._permitted = False
        self._withdrawn = False

    # ---- read-only ----
    def safe_for_honda(self) -> bool:
        return False  # hard guard; never True in this campaign

    def capability_query(self) -> FactoryCapability:
        return self._cap

    @property
    def admitted(self) -> bool:
        return self._admitted

    @property
    def permitted(self) -> bool:
        return self._permitted and not self._withdrawn

    # ---- forward gates (fail closed) ----
    def admit_receiver_session(self, *, evidence_tier: EvidenceTier) -> Decision:
        """Admit a secondary-stream receiver session. Denies unless the factory
        positively grants it AND the evidence is FACTORY_PROVEN. Never mints a
        session token."""
        if evidence_tier is not EvidenceTier.FACTORY_PROVEN:
            return _deny(R_SYNTHETIC_NOT_PROMOTABLE)
        if not self._cap.granted("receiver_admits_secondary_stream"):
            return _deny(R_FACTORY_CONTRACT_UNKNOWN)
        self._admitted = True
        return _grant()

    def permit_navigation_presentation(self) -> Decision:
        if not self._admitted:
            return _deny(R_NOT_ADMITTED)
        if not self._cap.granted("navigation_presentation_permitted"):
            return _deny(R_PRESENTATION_NOT_PERMITTED)
        self._permitted = True
        return _grant()

    def submit_frame_to_factory(self, *, evidence_tier: EvidenceTier) -> Decision:
        """Gate a frame submission toward the *factory* cluster sink. Always
        denied while ``safe_for_honda()`` is False; otherwise requires admitted +
        permitted + known frame sink + known geometry at FACTORY_PROVEN tier."""
        if not self.safe_for_honda():
            return _deny(R_SAFE_FOR_HONDA_FALSE)
        if evidence_tier is not EvidenceTier.FACTORY_PROVEN:
            return _deny(R_SYNTHETIC_NOT_PROMOTABLE)
        if not self.permitted:
            return _deny(R_NOT_ADMITTED if not self._admitted else R_PRESENTATION_NOT_PERMITTED)
        if not self._cap.granted("frame_sink_contract"):
            return _deny(R_FRAME_SINK_UNKNOWN)
        if not self._cap.granted("display_geometry_known"):
            return _deny(R_GEOMETRY_UNKNOWN)
        return _grant()

    # ---- safe-direction actions (always succeed) ----
    def withdraw_for_warning(self) -> Decision:
        """A factory warning/interrupt always wins: withdrawing custom content
        is unconditionally allowed. This does NOT assert that real factory
        warning priority is enforced downstream -- only that we always yield."""
        self._withdrawn = True
        self._permitted = False
        return _grant(R_OK_SAFE_DIRECTION)

    def on_source_death(self) -> Decision:
        return self._teardown()

    def on_host_death(self) -> Decision:
        return self._teardown()

    def revoke(self) -> Decision:
        return self._teardown()

    def cleanup(self) -> Decision:
        return self._teardown()

    def restore_factory(self) -> Decision:
        """Return to the stock state. Always available; it is the safe default."""
        self._teardown()
        return _grant(R_OK_SAFE_DIRECTION)

    def _teardown(self) -> Decision:
        self._admitted = False
        self._permitted = False
        self._withdrawn = True
        return _grant(R_OK_SAFE_DIRECTION)


def default_fail_closed_contract() -> FactoryIntegrationContract:
    """The honest current state: every factory fact UNKNOWN -> all forward gates deny."""
    return FactoryIntegrationContract(FactoryCapability())
