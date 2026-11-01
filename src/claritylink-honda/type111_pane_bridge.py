"""Type111 child stream -> Navigation pane bridge (CL-HONDA-111-01).

Original, offline, synthetic-only. Connects a parent-owned Type111 child
(``type111_child_authority``) to a pane host through a bounded, generation-gated
frame path. It never sees Type110: there is no parameter, field or call that
names the center-display stream, so the bridge cannot affect it by construction.

Lifecycle (single direction of authority: parent -> child -> lease -> frames):

    IDLE --start--> PENDING_PANE --attach--> STREAMING
                         ^                       |
                         |        lease revoked  v
                         +--resume-------- WITHDRAWN        any --child ends--> CLOSED

Rules (do not relax):
  * The bridge presents only while it holds a valid pane lease. When the lease
    is revoked (page change, interrupt, display loss, geometry change, newer
    lease) the queue is cleared, every buffered frame is released, and the
    bridge stays WITHDRAWN. Nothing is replayed after the cause clears.
  * ``resume`` is explicit, needs a live child and a pane host that grants a
    strictly newer pane generation, and only then accepts new frames.
  * When the child ends (disconnect, close, parent loss) the pane is withdrawn
    and the bridge is CLOSED for good; a new child needs a new grant.
  * Every frame offered is released exactly once, whatever happens to it.
  * A new VideoConfig opens a new config generation; frames from an earlier
    one are refused.
  * Surface-backed frames are refused: no Surface owner exists.
  * The real-facing sink (``FactorySinkAdapter``) always denies.
"""
from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
for _p in (_root / "claritylink-honda", _root / "claritylink-transport", _root / "claritylink-negotiation"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import frame_gate as fg  # noqa: E402
import factory_integration_contract as fic  # noqa: E402
import navigation_pane_host as nph  # noqa: E402
import type111_child_authority as tca  # noqa: E402

MAX_QUEUE = 8


class BridgeState(str, Enum):
    IDLE = "IDLE"
    PENDING_PANE = "PENDING_PANE"
    STREAMING = "STREAMING"
    WITHDRAWN = "WITHDRAWN"
    CLOSED = "CLOSED"


class OfferStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_NOT_STREAMING = "REJECTED_NOT_STREAMING"
    REJECTED_NO_CONFIG = "REJECTED_NO_CONFIG"
    REJECTED_STALE_CONFIG = "REJECTED_STALE_CONFIG"
    REJECTED_MALFORMED = "REJECTED_MALFORMED"
    REJECTED_IDENTITY = "REJECTED_IDENTITY"
    REJECTED_ORDER = "REJECTED_ORDER"
    REJECTED_UNSUPPORTED_STORAGE = "REJECTED_UNSUPPORTED_STORAGE"
    REJECTED_CHILD_ENDED = "REJECTED_CHILD_ENDED"


@dataclass
class BridgeStats:
    offered: int = 0
    accepted: int = 0
    rejected: int = 0
    dropped_oldest: int = 0
    presented: int = 0
    present_denied: int = 0
    withdrawals: int = 0
    released: int = 0
    resumes: int = 0
    config_changes: int = 0


class FactorySinkAdapter:
    """Pane host stand-in for the REAL factory path: always denies.

    It consults the fail-closed ``FactoryIntegrationContract`` and has no Honda
    service handle, so it cannot become a live sink. Used to prove the bridge
    withdraws and never presents when pointed at the factory side.
    """

    def __init__(self, contract: fic.FactoryIntegrationContract | None = None) -> None:
        self._contract = contract or fic.default_fail_closed_contract()

    def next_generation(self) -> int:
        return 1

    def acquire(self, owner: nph.PaneOwner) -> nph.AcquireResult:
        # Consult the contract so its counters and reasons stay truthful. Even a
        # hypothetical allow cannot turn this adapter into a sink: it owns no
        # Honda handle, so the answer is always a denial.
        self._contract.admit_receiver_session(evidence_tier=fic.EvidenceTier.SYNTHETIC)
        return nph.AcquireResult(nph.AcquireStatus.DENIED_NOT_ADMISSIBLE)

    def present(self, lease: object, frame: nph.DecodedFrame) -> nph.PresentResult:
        self._contract.submit_frame_to_factory(evidence_tier=fic.EvidenceTier.SYNTHETIC)
        return nph.PresentResult(nph.PresentStatus.DENIED_LEASE_INVALID, "factory_sink_denied")

    def withdraw(self, lease: object) -> None:
        self._contract.withdraw_for_warning()


class Type111PaneBridge:
    def __init__(self, parent: tca.ParentAuthority, host: nph.PaneHost, *, capacity: int = 2) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or not 1 <= capacity <= MAX_QUEUE:
            raise ValueError("capacity must be in 1..%d" % MAX_QUEUE)
        self._parent = parent
        self._host = host
        self._capacity = capacity
        self._lock = threading.RLock()
        self._state = BridgeState.IDLE
        self._child: tca.Type111Child | None = None
        self._lease: nph.PaneLease | None = None
        self._gate: fg.FrameGate | None = None
        self._pane_generation = 0
        self._config_generation = 0
        self._dimensions: tuple[int, int] | None = None
        self._last_end_reason: str | None = None
        self._last_withdraw_reason: str | None = None
        self.stats = BridgeStats()

    # ---- read-only ----
    @property
    def state(self) -> BridgeState:
        return self._state

    @property
    def child(self) -> tca.Type111Child | None:
        return self._child

    @property
    def config_generation(self) -> int:
        return self._config_generation

    @property
    def pane_generation(self) -> int:
        return self._pane_generation

    @property
    def end_reason(self) -> str | None:
        return self._last_end_reason

    @property
    def withdraw_reason(self) -> str | None:
        return self._last_withdraw_reason

    @property
    def queue_depth(self) -> int:
        return len(self._gate) if self._gate is not None else 0

    # ---- lifecycle ----
    def start(self, stream_connection_id: int) -> nph.AcquireStatus | None:
        """Open a child under the parent and try to take the pane. Returns the
        pane acquisition status, or ``None`` if the host call was not reached."""
        with self._lock:
            if self._state not in (BridgeState.IDLE, BridgeState.CLOSED):
                raise tca.AuthorityError("bridge_already_started")
            grant = self._parent.grant_child(stream_connection_id)
            child = self._parent.open_child(grant)
            self._child = child
            self._gate = fg.FrameGate(capacity=self._capacity, policy=fg.BackpressurePolicy.REJECT_NEW)
            self._gate.begin_generation(child.identity.stream_generation)
            self._lease = None
            self._config_generation = 0
            self._dimensions = None
            self._last_end_reason = None
            self._last_withdraw_reason = None
            self._state = BridgeState.PENDING_PANE
        child.add_end_callback(self._child_ended)
        return self._attach()

    def resume(self) -> nph.AcquireStatus | None:
        """Try again after a withdrawal, with a fresh pane generation. Requires a
        live child. Never replays anything that was buffered."""
        with self._lock:
            if self._state not in (BridgeState.WITHDRAWN, BridgeState.PENDING_PANE):
                return None
            if self._child is None or not self._child.live:
                return None
            self.stats.resumes += 1
        return self._attach()

    def stop(self) -> None:
        child = self._child
        if child is not None:
            child.close()
        with self._lock:
            if self._state is not BridgeState.CLOSED:
                self._close_locked("stopped")

    def video_config(self, width: int, height: int) -> int:
        """Accept a VideoConfig. A changed size opens a new config generation and
        drops frames queued under the old one."""
        for v, limit in ((width, nph.MAX_WIDTH), (height, nph.MAX_HEIGHT)):
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= limit:
                raise ValueError("invalid_video_config")
        with self._lock:
            child = self._child
            if child is None or not child.live or self._state is BridgeState.CLOSED:
                raise tca.AuthorityError("no_live_child")
            if (width, height) != self._dimensions:
                self._dimensions = (width, height)
                self._config_generation += 1
                self.stats.config_changes += 1
                self._clear_queue_locked()
            return self._config_generation

    # ---- frame path ----
    def offer(self, frame: nph.DecodedFrame) -> OfferStatus:
        """Queue one decoded frame. The frame is released exactly once on every
        path: dropped, rejected, withdrawn or presented."""
        with self._lock:
            self.stats.offered += 1
            status = self._offer_locked(frame)
            if status is OfferStatus.ACCEPTED:
                self.stats.accepted += 1
            else:
                self.stats.rejected += 1
                self._release(frame)
            return status

    def _offer_locked(self, frame: nph.DecodedFrame) -> OfferStatus:
        if not isinstance(frame, nph.DecodedFrame):
            return OfferStatus.REJECTED_MALFORMED
        child = self._child
        if self._state is BridgeState.CLOSED or child is None:
            return OfferStatus.REJECTED_CHILD_ENDED
        if not child.live:
            self._child_gone_locked("child_not_live")
            return OfferStatus.REJECTED_CHILD_ENDED
        if self._state is not BridgeState.STREAMING or self._lease is None or not self._lease.valid:
            return OfferStatus.REJECTED_NOT_STREAMING
        if self._dimensions is None:
            return OfferStatus.REJECTED_NO_CONFIG
        problem = frame.validate()
        if problem is not None:
            return OfferStatus.REJECTED_MALFORMED
        if frame.storage is not nph.FrameStorage.CPU_BUFFER:
            return OfferStatus.REJECTED_UNSUPPORTED_STORAGE
        ident = child.identity
        if (frame.stream_connection_id != ident.stream_connection_id or
                frame.parent_generation != ident.parent_generation or
                frame.stream_generation != ident.stream_generation):
            return OfferStatus.REJECTED_IDENTITY
        if frame.config_generation != self._config_generation:
            return OfferStatus.REJECTED_STALE_CONFIG
        assert self._gate is not None
        if len(self._gate) >= self._capacity:
            oldest = self._gate.poll()
            if oldest is not None:
                self.stats.dropped_oldest += 1
                self._release(oldest.payload)
        gate_status = self._gate.offer(fg.Frame(
            generation=frame.stream_generation, sequence=frame.sequence,
            timestamp=frame.presentation_time_ns, payload=frame))
        if gate_status is not fg.FrameStatus.ACCEPTED:
            return OfferStatus.REJECTED_ORDER
        return OfferStatus.ACCEPTED

    def pump(self) -> nph.PresentResult | None:
        """Present the freshest queued frame; older ones are released unseen."""
        with self._lock:
            if self._gate is None or self._state is not BridgeState.STREAMING:
                return None
            latest = None
            while True:
                item = self._gate.poll()
                if item is None:
                    break
                if latest is not None:
                    self.stats.dropped_oldest += 1
                    self._release(latest.payload)
                latest = item
            if latest is None:
                return None
            frame = latest.payload
            lease = self._lease
            if lease is None:
                self._release(frame)
                return nph.PresentResult(nph.PresentStatus.DENIED_LEASE_INVALID, "no_lease")
            result = self._host.present(lease, frame)
            if result.presented:
                self.stats.presented += 1
            else:
                self.stats.present_denied += 1
            self._release(frame)
            return result

    # ---- internals ----
    def _attach(self) -> nph.AcquireStatus | None:
        with self._lock:
            child = self._child
            if child is None or not child.live or self._state is BridgeState.CLOSED:
                return None
            self._pane_generation = max(self._pane_generation + 1, self._host.next_generation())
            owner = nph.PaneOwner(child.identity.stream_connection_id,
                                  child.identity.parent_generation, self._pane_generation)
        result = self._host.acquire(owner)
        if not result.granted:
            return result.status
        lease = result.lease
        assert lease is not None
        with self._lock:
            if self._state is BridgeState.CLOSED or not (self._child and self._child.live):
                self._host.withdraw(lease)
                return None
            self._lease = lease
            self._state = BridgeState.STREAMING
            self._last_withdraw_reason = None
        lease.add_revoke_callback(self._lease_revoked)
        return result.status

    def _lease_revoked(self, reason: str) -> None:
        with self._lock:
            if self._state is BridgeState.STREAMING:
                self._state = BridgeState.WITHDRAWN
                self._last_withdraw_reason = reason
                self.stats.withdrawals += 1
            self._lease = None
            self._clear_queue_locked()

    def _child_ended(self, reason: str) -> None:
        with self._lock:
            self._child_gone_locked(reason)

    def _child_gone_locked(self, reason: str) -> None:
        if self._state is BridgeState.CLOSED:
            return
        lease = self._lease
        self._close_locked(reason)
        if lease is not None:
            self._host.withdraw(lease)   # safe direction; host may already have revoked

    def _close_locked(self, reason: str) -> None:
        self._state = BridgeState.CLOSED
        self._last_end_reason = reason
        self._lease = None
        self._clear_queue_locked()
        if self._gate is not None:
            self._gate.close()

    def _clear_queue_locked(self) -> None:
        gate = self._gate
        if gate is None or gate.closed:
            return
        while True:
            item = gate.poll()
            if item is None:
                break
            self._release(item.payload)

    def _release(self, frame: object) -> None:
        if isinstance(frame, nph.DecodedFrame) and not frame._released:
            self.stats.released += 1
            frame.release()
