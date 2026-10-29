"""Integrated synthetic structured-navigation pipeline (CL-FACTORY-02 / P0).

Original, offline, synthetic-only orchestration that ties three already-reviewed
ClarityLink primitives together behind one explicit, stable interface:

  * ``frame_gate.FrameGate``              -- per-generation transport freshness
    (strictly increasing sequence, non-decreasing timestamp, bounded buffer).
  * ``cluster_navigation_model``          -- structured turn-by-turn navigation
    state (session identity, generation, visibility, warning withdrawal,
    source/host death, recovery, restoration).
  * ``factory_integration_contract``      -- fail-closed factory admission. It is
    never granted here: ``safe_for_honda()`` stays False, so every factory-facing
    submission is denied.

The pipeline distinguishes four outcomes for every submitted update, because they
are genuinely different things and the product must never conflate them:

  1. accepted into **transport**            (passed freshness/ownership)
  2. accepted into **navigation state**     (applied to the structured model)
  3. eligible for **synthetic presentation** (our own simulated host could show it)
  4. **rejected because factory output is unavailable** (the real cluster sink is
     never available in this campaign -> factory presentation is always denied)

Hard boundaries (do not relax): no Honda Binder/IPC, no proprietary identifiers,
no authentication, no real Display 1, no key material. A structured navigation
update is a *semantic* message; it is NOT a decoded Type111 video frame and this
module never converts one into the other. ``safe_for_honda()`` is always False.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Sibling project packages (same layout the integration tests use).
_SRC = Path(__file__).resolve().parents[1]
for _p in ("claritylink-transport", "claritylink-honda"):
    _ps = str(_SRC / _p)
    if _ps not in sys.path:
        sys.path.insert(0, _ps)

import frame_gate as fg  # noqa: E402
import cluster_navigation_model as nav  # noqa: E402
import factory_integration_contract as fic  # noqa: E402


class PipelineState(str, Enum):
    IDLE = "IDLE"            # no session opened yet
    ACTIVE = "ACTIVE"        # a navigation session owns a generation
    INTERRUPTED = "INTERRUPTED"
    SOURCE_LOST = "SOURCE_LOST"
    HOST_LOST = "HOST_LOST"
    RECOVERING = "RECOVERING"
    CLOSED = "CLOSED"


class Admission(str, Enum):
    """Top-level disposition of one submitted update."""
    ACCEPTED = "ACCEPTED"                      # into transport AND navigation state
    REJECTED_MALFORMED = "REJECTED_MALFORMED"  # content invalid; transport untouched
    REJECTED_TRANSPORT = "REJECTED_TRANSPORT"  # failed freshness/ownership at the gate
    REJECTED_NAV = "REJECTED_NAV"              # passed transport but navigation model refused
    REJECTED_NOT_OPEN = "REJECTED_NOT_OPEN"    # no active session / pipeline not accepting


# Reason codes for presentation eligibility (stable, machine-checkable).
P_ELIGIBLE_SYNTHETIC = "ELIGIBLE_SYNTHETIC"
P_NO_SESSION = "NO_SESSION"
P_NOT_VISIBLE = "NOT_VISIBLE"
P_WITHDRAWN = "WITHDRAWN"
P_FACTORY_OUTPUT_UNAVAILABLE = "FACTORY_OUTPUT_UNAVAILABLE"
P_UPDATE_REJECTED = "UPDATE_REJECTED"  # this update was not accepted; nothing to present


@dataclass(frozen=True)
class UpdateOutcome:
    """Explicit, four-way disposition of a single submitted update."""
    admission: Admission
    transport_status: fg.FrameStatus | None            # None if transport never consulted
    nav_status: nav.UpdateStatus | None                # None if nav never consulted
    presentation_eligible: bool                        # synthetic host only
    presentation_reason: str
    factory_decision: fic.Decision                     # always denied (safe_for_honda False)

    @property
    def accepted_into_transport(self) -> bool:
        return self.transport_status is fg.FrameStatus.ACCEPTED

    @property
    def accepted_into_nav(self) -> bool:
        return self.nav_status is nav.UpdateStatus.APPLIED

    @property
    def accepted(self) -> bool:
        return self.admission is Admission.ACCEPTED


@dataclass
class PipelineStats:
    opened_sessions: int = 0
    submitted: int = 0
    accepted: int = 0
    rejected_malformed: int = 0
    rejected_transport: int = 0
    rejected_nav: int = 0
    rejected_not_open: int = 0
    presentation_eligible: int = 0
    factory_denied: int = 0
    warnings: int = 0
    source_deaths: int = 0
    host_losses: int = 0
    recoveries: int = 0
    restorations: int = 0


class SyntheticNavigationPipeline:
    """Coordinates transport freshness + navigation state + fail-closed factory
    admission for a single structured-navigation presentation on a *simulated*
    cluster area. Entirely offline; owns no real display.

    ``host_available`` models whether a (synthetic) display host is present. The
    real factory output is modeled as permanently unavailable: factory-facing
    submission is always denied by the contract's ``safe_for_honda()`` guard.
    """

    def __init__(
        self,
        *,
        capacity: int = 8,
        policy: fg.BackpressurePolicy = fg.BackpressurePolicy.DROP_OLDEST,
        contract: fic.FactoryIntegrationContract | None = None,
    ) -> None:
        self._gate = fg.FrameGate(capacity=capacity, policy=policy)
        self._nav = nav.ClusterNavigationModel()
        self._contract = contract or fic.default_fail_closed_contract()
        self._state = PipelineState.IDLE
        self._session_id: int | None = None
        self._generation: int | None = None
        # Highest generation ever opened in this pipeline's lifetime. It persists
        # across restore_factory() so a prior generation number can NEVER be
        # reused -- stale stream authority cannot be resurrected after a restart.
        self._gen_high_water = 0
        self._host_available = False
        self.stats = PipelineStats()

    # ---- read-only views ----
    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def generation(self) -> int | None:
        return self._generation

    @property
    def session_id(self) -> int | None:
        return self._session_id

    @property
    def current(self) -> nav.NavigationUpdate | None:
        return self._nav.current

    @property
    def nav_state(self) -> nav.NavState:
        return self._nav.state

    @property
    def host_available(self) -> bool:
        return self._host_available

    @property
    def queue_depth(self) -> int:
        return len(self._gate)

    def safe_for_honda(self) -> bool:
        return self._contract.safe_for_honda()  # always False

    def presentable_to_factory(self) -> bool:
        return self._nav.presentable_to_factory()  # always False

    # ---- simulated display-host availability ----
    def set_host_available(self, available: bool) -> None:
        self._host_available = bool(available)

    # ---- session lifecycle ----
    def open_session(self, session_id: int, generation: int) -> None:
        """Open (or restart) a navigation session. ``generation`` must strictly
        increase across the pipeline's lifetime; both transport and navigation
        adopt the same generation so their freshness rules stay aligned."""
        if self._state is PipelineState.CLOSED:
            raise RuntimeError("pipeline is closed")
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise ValueError("generation must be an int")
        # Lifetime-monotonic: a generation number is never reusable, even after a
        # full restore (fail-closed against stale-authority resurrection).
        if generation <= self._gen_high_water:
            raise ValueError(
                f"generation must exceed lifetime high-water ({self._gen_high_water})")
        # Both raise on a non-strictly-increasing generation (fail-closed).
        self._gate.begin_generation(generation)
        self._nav.start_session(session_id=session_id, generation=generation)
        self._session_id = session_id
        self._generation = generation
        self._gen_high_water = generation
        self._state = PipelineState.ACTIVE
        self.stats.opened_sessions += 1

    def submit_update(
        self,
        *,
        generation: int,
        sequence: int,
        timestamp: int,
        maneuver,
        distance: int,
        unit,
        road_name: str = "",
    ) -> UpdateOutcome:
        """Validate content, then transport freshness, then navigation state, in
        that order. The three steps map to the four explicit outcomes."""
        self.stats.submitted += 1
        factory = self._deny_factory()  # recomputed every call; always denied

        if self._state is not PipelineState.ACTIVE:
            self.stats.rejected_not_open += 1
            return self._outcome(Admission.REJECTED_NOT_OPEN, None, None, factory)

        # 1) content validation (does not touch transport or nav on failure)
        try:
            update = nav.NavigationUpdate.build(
                generation, sequence, maneuver, distance, unit, road_name)
        except nav.MalformedUpdate:
            self.stats.rejected_malformed += 1
            return self._outcome(Admission.REJECTED_MALFORMED, None, None, factory)

        # 2) transport freshness / generation ownership
        frame = fg.Frame(generation=generation, sequence=sequence,
                         timestamp=timestamp, payload=update)
        tstatus = self._gate.offer(frame)
        if tstatus is not fg.FrameStatus.ACCEPTED:
            self.stats.rejected_transport += 1
            return self._outcome(Admission.REJECTED_TRANSPORT, tstatus, None, factory)

        # transport accepted -> hand the structured payload to the nav state.
        polled = self._gate.poll()
        assert polled is frame  # single-consumer: we drain exactly what we offered
        nstatus = self._nav.apply_update(update)
        if nstatus is not nav.UpdateStatus.APPLIED:
            self.stats.rejected_nav += 1
            return self._outcome(Admission.REJECTED_NAV, tstatus, nstatus, factory)

        self.stats.accepted += 1
        return self._outcome(Admission.ACCEPTED, tstatus, nstatus, factory)

    # ---- warnings / interruption (fail-safe: always yield) ----
    def on_warning(self) -> None:
        """A (synthetic) factory warning: custom content withdraws immediately."""
        self.stats.warnings += 1
        self._contract.withdraw_for_warning()
        self._nav.interrupt()
        if self._state is PipelineState.ACTIVE:
            self._state = PipelineState.INTERRUPTED

    def clear_warning(self) -> None:
        self._nav.clear_interrupt()
        if self._state is PipelineState.INTERRUPTED:
            self._state = (PipelineState.ACTIVE
                           if self._nav.state is nav.NavState.ACTIVE else PipelineState.IDLE)

    # ---- death / host / recovery / restore ----
    def on_source_death(self) -> None:
        self.stats.source_deaths += 1
        self._gate.on_source_death()
        self._nav.on_source_death()
        self._contract.on_source_death()
        self._state = PipelineState.SOURCE_LOST

    def on_host_lost(self) -> None:
        self.stats.host_losses += 1
        self._host_available = False
        self._nav.on_host_lost()
        self._contract.on_host_death()
        # the prior transport generation is abandoned on host loss.
        self._gate.close()
        self._state = PipelineState.HOST_LOST

    def begin_recovery(self) -> None:
        if self._state is PipelineState.HOST_LOST:
            self._nav.begin_recovery()
            self._state = PipelineState.RECOVERING
            self.stats.recoveries += 1

    def restore_factory(self) -> None:
        """Return to the stock/default: no custom content, fresh transport. A new
        session (with a strictly greater generation) is required to present again."""
        self.stats.restorations += 1
        self._nav.restore_factory()
        self._contract.restore_factory()
        self._host_available = False
        # fresh gate so no stale frame/generation can survive a restart.
        self._gate = fg.FrameGate(capacity=self._gate._capacity, policy=self._gate._policy)
        self._session_id = None
        self._generation = None
        self._state = PipelineState.IDLE

    def shutdown(self) -> None:
        self._gate.close()
        self._nav.restore_factory()
        self._contract.cleanup()
        self._host_available = False
        self._session_id = None
        self._generation = None
        self._state = PipelineState.CLOSED

    # ---- presentation eligibility (synthetic only) ----
    def presentation_eligibility(self) -> tuple[bool, str]:
        """Whether the *synthetic* host could present the current nav content.
        This is never factory presentation (that is always denied)."""
        if self._state is not PipelineState.ACTIVE or self._session_id is None:
            return (False, P_NO_SESSION)
        if not self._nav.visible:
            if self._nav.state in (nav.NavState.INTERRUPTED, nav.NavState.WITHDRAWN):
                return (False, P_WITHDRAWN)
            return (False, P_NOT_VISIBLE)
        if not self._host_available:
            return (False, P_FACTORY_OUTPUT_UNAVAILABLE)
        return (True, P_ELIGIBLE_SYNTHETIC)

    # ---- internals ----
    def _deny_factory(self) -> fic.Decision:
        d = self._contract.submit_frame_to_factory(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN)
        # Even with the strongest (hypothetical) evidence tier, the guard denies.
        assert d.allowed is False and d.reason_code == fic.R_SAFE_FOR_HONDA_FALSE
        self.stats.factory_denied += 1
        return d

    def _outcome(self, admission, tstatus, nstatus, factory) -> UpdateOutcome:
        # Presentation eligibility is a per-update property: only an update that
        # was actually accepted into navigation state can be eligible. A rejected
        # update is never presentable, regardless of the pipeline's state.
        if admission is Admission.ACCEPTED:
            eligible, reason = self.presentation_eligibility()
        else:
            eligible, reason = False, P_UPDATE_REJECTED
        if eligible:
            self.stats.presentation_eligible += 1
        return UpdateOutcome(
            admission=admission,
            transport_status=tstatus,
            nav_status=nstatus,
            presentation_eligible=eligible,
            presentation_reason=reason,
            factory_decision=factory,
        )
