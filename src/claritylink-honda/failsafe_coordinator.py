"""Disconnect fail-safe for a hypothetical Type111 -> Display 1 path (CL-INT-03).

Original, offline, synthetic-only. Enforces the design target
``CARPLAY_DISCONNECTED => FACTORY_BEHAVIOR_ONLY`` on a *simulated* cluster host
(``SimulatedClusterHost``). It is a target model, not evidence about a Honda:
no Honda IPC, no real Display 1, no key material, ``safe_for_honda()`` False.

Two layers, deliberately independent so that cleanup never rests on one clean
disconnect callback:

  * ``Display1LeaseHost`` -- the HOST-owned fence. It alone decides whether
    custom content is visible. Content needs an unexpired lease bound to a boot
    epoch and a strictly increasing generation. Expiry is evaluated lazily on
    every read and submit, so a dead coordinator, receiver or decoder (no
    ``tick()``, no callback) still ends in factory-only output once the lease
    runs out. Nothing here depends on ClarityLink being alive.
  * ``FailSafeCoordinator`` -- the project-side state machine. On any fault it
    revokes the host first (visible content), then runs each registered
    project cleanup independently so one failing closer cannot block the rest.

Safe-direction actions (revoke, fault, cleanup, restore) always succeed.

Limits: the epoch and lease are staleness fences, not authenticators (a caller
able to read host memory can forge them). Expiry is lazy on every read, and a
host-owned timer (``display1_host_service.Display1HostService``, CL-INT-04) calls
``enforce_expiry`` so withdrawal never waits on a read. Host methods are
serialized by one re-entrant lock so that timer and request threads are safe.
"""
from __future__ import annotations

import secrets
import sys
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import monotonic
from typing import Any, Callable

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import simulated_cluster_host as sch  # noqa: E402

DEFAULT_LEASE_SECONDS = 1.0
FRAME_AGE_LIMIT_LEASES = 2.0  # heartbeats alone may not outlive this many leases
_HOST_SESSION_ID = 1  # single project-owned Type111 session slot on the host


class SubmitResult(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_NO_LEASE = "REJECTED_NO_LEASE"
    REJECTED_EPOCH = "REJECTED_EPOCH"
    REJECTED_STALE_GENERATION = "REJECTED_STALE_GENERATION"
    REJECTED_OUT_OF_ORDER = "REJECTED_OUT_OF_ORDER"
    REJECTED_INTERRUPTED = "REJECTED_INTERRUPTED"
    REJECTED_NO_DISPLAY = "REJECTED_NO_DISPLAY"


class GrantResult(str, Enum):
    GRANTED = "GRANTED"
    REJECTED_WITHDRAWAL_PENDING = "REJECTED_WITHDRAWAL_PENDING"
    REJECTED_STALE_GENERATION = "REJECTED_STALE_GENERATION"
    REJECTED_INTERRUPTED = "REJECTED_INTERRUPTED"
    REJECTED_NO_DISPLAY = "REJECTED_NO_DISPLAY"


@dataclass(frozen=True)
class LeaseGrant:
    """Names one host epoch and generation. A staleness fence, not unforgeable."""

    epoch: int
    generation: int


DIAGNOSTIC_LOG_LIMIT = 1024  # bounded memory; the IPC status reply carries only the newest few


def _append_bounded(log: list[str], item: str) -> None:
    log.append(item)
    if len(log) > DIAGNOSTIC_LOG_LIMIT:
        del log[: len(log) - DIAGNOSTIC_LOG_LIMIT]


def _require_nonneg_int(value: Any, name: str) -> None:
    """Reject bool/float/NaN/negative: a NaN would disable monotonic comparisons."""
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")


class Display1LeaseHost:
    """Host-owned revocable fence in front of the simulated cluster host."""

    def __init__(
        self,
        *,
        lease_seconds: float = DEFAULT_LEASE_SECONDS,
        clock: Callable[[], float] = monotonic,
        epoch: int | None = None,
        frame_age_limit: float | None = None,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self._lease_seconds = lease_seconds
        self._frame_age_limit = (
            FRAME_AGE_LIMIT_LEASES * lease_seconds if frame_age_limit is None else frame_age_limit
        )
        if self._frame_age_limit < lease_seconds:
            raise ValueError("frame_age_limit must be at least lease_seconds")
        self._clock = clock
        self._lock = threading.RLock()
        # Fresh per host instance: a lease from a prior boot can never match.
        self.epoch = secrets.randbits(32) if epoch is None else epoch
        self._cluster = sch.SimulatedClusterHost()
        self._cluster.connect_display()
        self._lease: LeaseGrant | None = None
        self._deadline = 0.0
        self._last_frame_at = 0.0
        self._last_sequence = -1
        self._generation_high_water = 0
        self._page_selected = False
        self._withdrawal_pending = False  # a cluster withdrawal raised and has not yet succeeded
        # Bounded diagnostics (newest last): a host that keeps failing must not grow without limit
        # or make its own status reply too large to read. The counters never wrap or trim.
        self.revocations: list[str] = []
        self.withdrawal_failures: list[str] = []
        self.revocation_count = 0
        self.withdrawal_failure_count = 0

    # ---- read side: lazily fail closed, no tick required ----
    @property
    def visible_content(self) -> Any:
        """What the user would see from ClarityLink. None means factory only.

        After a failed withdrawal this reports what the cluster still holds: the
        lease is gone but the content is not, and saying otherwise would be false.
        """
        with self._lock:
            self._expire_if_needed()
            if not self._page_selected or not self._cluster.main_presentable():
                return None
            if self._lease is None and not self._withdrawal_pending:
                return None
            return self._cluster.main_content

    @property
    def lease_held(self) -> bool:
        with self._lock:
            self._expire_if_needed()
            return self._lease is not None

    @property
    def generation_high_water(self) -> int:
        """Highest generation ever granted by this host instance (a fence, never lowered)."""
        with self._lock:
            return self._generation_high_water

    @property
    def withdrawal_pending(self) -> bool:
        """True while a cluster withdrawal has failed and project content may remain."""
        with self._lock:
            return self._withdrawal_pending

    @property
    def residual_state(self) -> tuple[Any, ...]:
        """Everything project-owned still held by the host (empty when clean)."""
        with self._lock:
            self._expire_if_needed()
            return tuple(
                item for item in (self._lease, self._cluster.main_owner, self._cluster.main_content)
                if item is not None
            )

    def enforce_expiry(self) -> bool:
        """Timer entry point: apply expiry and retry a failed withdrawal. True if state changed."""
        with self._lock:
            before = (self._lease, self._withdrawal_pending, self.revocation_count)
            try:
                self._expire_if_needed()  # fence already closed if this raises
            except Exception:  # noqa: BLE001
                if not self._withdrawal_pending:
                    raise  # not a withdrawal failure: the watchdog must count and report it
            if self._withdrawal_pending:
                self._withdraw_cluster()
            return before != (self._lease, self._withdrawal_pending, self.revocation_count)

    def next_deadline(self) -> float | None:
        """Earliest clock time at which the held lease must be revoked; None if no lease."""
        with self._lock:
            if self._lease is None:
                return None
            return min(self._deadline, self._last_frame_at + self._frame_age_limit)

    def now(self) -> float:
        return self._clock()

    def _expire_if_needed(self) -> None:
        if self._lease is None:
            return
        now = self._clock()
        if now >= self._deadline:
            self.revoke("lease expired")
        elif now - self._last_frame_at >= self._frame_age_limit:
            self.revoke("no frame progress")  # frozen frame: heartbeats cannot hold it

    # ---- grant / submit / heartbeat ----
    def grant(self, generation: int) -> tuple[GrantResult, LeaseGrant | None]:
        """Issue a lease. A newer generation atomically supersedes the old one."""
        _require_nonneg_int(generation, "generation")
        with self._lock:
            return self._grant_locked(generation)

    def grant_above(self, minimum: int) -> tuple[GrantResult, LeaseGrant | None]:
        """Grant the host's next generation, at least ``minimum``.

        For a producer in another process whose own counter restarts at 1: the HOST is the
        authority on generations, so allocation and grant happen under one lock.
        """
        _require_nonneg_int(minimum, "minimum")
        with self._lock:
            return self._grant_locked(max(minimum, self._generation_high_water + 1))

    def _grant_locked(self, generation: int) -> tuple[GrantResult, LeaseGrant | None]:
        self._expire_if_needed()
        if self._withdrawal_pending and not self._withdraw_cluster():
            return GrantResult.REJECTED_WITHDRAWAL_PENDING, None
        if not self._cluster.display_available:
            return GrantResult.REJECTED_NO_DISPLAY, None
        if self._cluster.interrupt_active:
            return GrantResult.REJECTED_INTERRUPTED, None
        if generation <= self._generation_high_water:
            return GrantResult.REJECTED_STALE_GENERATION, None
        if self._lease is not None:
            self.revoke("superseded by newer generation")
        self._generation_high_water = generation
        self._lease = LeaseGrant(self.epoch, generation)
        self._deadline = self._clock() + self._lease_seconds
        self._last_frame_at = self._clock()
        self._last_sequence = -1
        return GrantResult.GRANTED, self._lease

    def submit(self, lease: LeaseGrant, sequence: int, content: Any) -> SubmitResult:
        _require_nonneg_int(sequence, "sequence")
        with self._lock:
            return self._submit_locked(lease, sequence, content)

    def _submit_locked(self, lease: LeaseGrant, sequence: int, content: Any) -> SubmitResult:
        self._expire_if_needed()
        rejection = self._check_lease(lease)
        if rejection is not None:
            return rejection
        if sequence <= self._last_sequence:
            return SubmitResult.REJECTED_OUT_OF_ORDER
        result = self._cluster.present_main(
            session_id=_HOST_SESSION_ID, generation=lease.generation, content=content
        )
        if result is sch.PresentResult.REJECTED_INTERRUPTED:
            return SubmitResult.REJECTED_INTERRUPTED
        if result in (sch.PresentResult.REJECTED_NO_DISPLAY, sch.PresentResult.REJECTED_CLOSED):
            return SubmitResult.REJECTED_NO_DISPLAY
        if result is sch.PresentResult.REJECTED_STALE_GENERATION:
            return SubmitResult.REJECTED_STALE_GENERATION
        self._last_sequence = sequence
        self._deadline = self._last_frame_at = self._clock()
        self._deadline += self._lease_seconds  # an accepted frame doubles as heartbeat
        return SubmitResult.ACCEPTED

    def heartbeat(self, lease: LeaseGrant) -> bool:
        with self._lock:
            self._expire_if_needed()
            if self._check_lease(lease) is not None:
                return False
            self._deadline = self._clock() + self._lease_seconds
            return True

    def _check_lease(self, lease: LeaseGrant) -> SubmitResult | None:
        if self._lease is None:
            return SubmitResult.REJECTED_NO_LEASE
        if lease.epoch != self.epoch:
            return SubmitResult.REJECTED_EPOCH
        if lease != self._lease:
            return SubmitResult.REJECTED_STALE_GENERATION
        return None

    # ---- safe-direction controls (idempotent; the lease fence always closes) ----
    def revoke(self, reason: str) -> bool:
        with self._lock:
            had_state = self._lease is not None or self._cluster.main_owner is not None
            self._lease = None  # the fence closes first: no submit can win after this line
            self._last_sequence = -1
            if had_state:
                self.revocation_count += 1
                _append_bounded(self.revocations, reason)
            self._withdraw_cluster(reraise=True)
            return had_state

    def revoke_if_current(self, lease: LeaseGrant, reason: str) -> bool:
        """Revoke only if ``lease`` is still the held lease (check and revoke are atomic).

        A stale owner's death or late cleanup therefore cannot withdraw a newer generation.
        The fence is closed even if the cluster withdrawal then raises (see
        ``withdrawal_pending``), so a raise is reported by state, not propagated.
        """
        with self._lock:
            if self._lease is None or self._lease != lease:
                return False
            try:
                return self.revoke(reason)
            except Exception:  # noqa: BLE001 - fence closed; failure recorded in withdrawal_pending
                return True

    def _withdraw_cluster(self, *, reraise: bool = False) -> bool:
        """Withdraw cluster content. A failure is recorded and retried; it is never hidden.

        ``reraise`` lets a caller that owns cleanup reporting (the ingest pipeline) see the
        failure; the timer path passes False and reports it through ``withdrawal_pending``.
        """
        try:
            self._cluster.withdraw_main()
        except Exception as exc:  # noqa: BLE001 - recorded, then re-raised or reported
            self._withdrawal_pending = True
            self.withdrawal_failure_count += 1
            _append_bounded(self.withdrawal_failures, type(exc).__name__)
            if reraise:
                raise
            return False
        self._withdrawal_pending = False
        return True

    def select_page(self, selected: bool) -> None:
        """Navigation page (de)selection hides content; it never grants or keeps it."""
        with self._lock:
            self._page_selected = bool(selected)

    def activate_interrupt(self) -> None:
        """Factory warning: preempts and revokes. Never re-exposes on clear."""
        with self._lock:
            self._cluster.activate_interrupt()
            self.revoke("factory interrupt")

    def clear_interrupt(self) -> None:
        with self._lock:
            self._cluster.clear_interrupt()

    def lose_display(self) -> None:
        with self._lock:
            self._cluster.lose_display()
            self.revoke("display lost")

    def restore_display(self) -> bool:
        with self._lock:
            self._cluster.begin_restore()
            return self._cluster.complete_restore(display_valid=True)


class LinkState(str, Enum):
    FACTORY_ONLY = "FACTORY_ONLY"
    PHONE_PRESENT = "PHONE_PRESENT"
    CARPLAY_ACTIVE = "CARPLAY_ACTIVE"
    TYPE111_NEGOTIATED = "TYPE111_NEGOTIATED"
    STREAMING = "STREAMING"


class Fault(str, Enum):
    USB_UNPLUG = "USB_UNPLUG"
    CARPLAY_ENDED = "CARPLAY_ENDED"
    TYPE111_TRANSPORT_FAILURE = "TYPE111_TRANSPORT_FAILURE"
    RECEIVER_DEATH = "RECEIVER_DEATH"
    DECODER_DEATH = "DECODER_DEATH"
    DISPLAY_HOST_RESTART = "DISPLAY_HOST_RESTART"
    INIT_FAILURE = "INIT_FAILURE"
    FACTORY_WARNING = "FACTORY_WARNING"


# State after the custom path is withdrawn. Anything that takes the receiver or
# the phone link down returns to factory-only; faults local to Type111 leave the
# primary CarPlay state (not owned by this module) alone.
_STATE_RANK = {
    LinkState.FACTORY_ONLY: 0,
    LinkState.PHONE_PRESENT: 1,
    LinkState.CARPLAY_ACTIVE: 2,
    LinkState.TYPE111_NEGOTIATED: 3,
    LinkState.STREAMING: 4,
}

_STATE_AFTER_FAULT = {
    Fault.USB_UNPLUG: LinkState.FACTORY_ONLY,
    Fault.RECEIVER_DEATH: LinkState.FACTORY_ONLY,
    Fault.CARPLAY_ENDED: LinkState.PHONE_PRESENT,
    Fault.TYPE111_TRANSPORT_FAILURE: LinkState.CARPLAY_ACTIVE,
    Fault.DECODER_DEATH: LinkState.CARPLAY_ACTIVE,
    Fault.DISPLAY_HOST_RESTART: LinkState.CARPLAY_ACTIVE,
    Fault.INIT_FAILURE: LinkState.CARPLAY_ACTIVE,
    Fault.FACTORY_WARNING: LinkState.CARPLAY_ACTIVE,
}


@dataclass(frozen=True)
class CleanupReport:
    reason: str
    ran: tuple[str, ...]
    failed: tuple[str, ...]


@dataclass
class _Closer:
    name: str
    close: Callable[[], None]


@dataclass
class FailSafeCoordinator:
    host: Display1LeaseHost
    state: LinkState = LinkState.FACTORY_ONLY
    reports: list[CleanupReport] = field(default_factory=list)
    _closers: list[_Closer] = field(default_factory=list)
    _lease: LeaseGrant | None = None
    _sequence: int = 0
    _next_generation: int = 1

    @property
    def lease(self) -> LeaseGrant | None:
        """The lease this coordinator currently holds (read-only; None when withdrawn)."""
        return self._lease

    @property
    def sequence(self) -> int:
        """Sequence the next ``submit_frame`` will carry to the host."""
        return self._sequence

    # ---- forward path: each step is explicit and can be refused ----
    def phone_attached(self) -> None:
        if self.state is LinkState.FACTORY_ONLY:
            self.state = LinkState.PHONE_PRESENT

    def carplay_started(self) -> None:
        if self.state is LinkState.PHONE_PRESENT:
            self.state = LinkState.CARPLAY_ACTIVE

    def type111_negotiated(self, closers: dict[str, Callable[[], None]] | None = None) -> bool:
        """Grant a lease for a new generation and take ownership of closers."""
        if self.state not in (LinkState.CARPLAY_ACTIVE, LinkState.TYPE111_NEGOTIATED,
                              LinkState.STREAMING):
            self._run_closers_only(closers)
            return False
        if self._lease is not None:
            self._withdraw("superseded by renegotiation")
        for name, close in (closers or {}).items():
            self._closers.append(_Closer(name, close))
        result, lease = self.host.grant(self._next_generation)
        self._next_generation += 1
        if lease is None:
            self._withdraw(f"grant refused: {result.value}")
            return False
        self._lease, self._sequence = lease, 0
        self.state = LinkState.TYPE111_NEGOTIATED
        return True

    def submit_frame(self, content: Any) -> SubmitResult:
        if self._lease is None:
            return SubmitResult.REJECTED_NO_LEASE
        result = self.host.submit(self._lease, self._sequence, content)
        self._sequence += 1
        if result is SubmitResult.ACCEPTED:
            self.state = LinkState.STREAMING
        else:
            self.sync()
        return result

    def heartbeat(self) -> bool:
        alive = self._lease is not None and self.host.heartbeat(self._lease)
        if not alive:
            self.sync()
        return alive

    # ---- fail-safe path ----
    def fault(self, kind: Fault) -> CleanupReport:
        """Withdraw everything custom and lower the state. Every closer runs; a host that cannot
        confirm the revoke is reported by raising AFTER cleanup (callers that own reporting catch it)."""
        if kind is Fault.FACTORY_WARNING:
            self.host.activate_interrupt()
        elif kind is Fault.DISPLAY_HOST_RESTART:
            self.host.lose_display()
            self.host.restore_display()
        try:
            return self._withdraw(kind.value)
        finally:
            target = _STATE_AFTER_FAULT[kind]
            if _STATE_RANK[target] < _STATE_RANK[self.state]:
                self.state = target  # a fault only ever lowers the state, never raises it

    def sync(self) -> None:
        """Adopt a host-side revocation (expiry, supersession) the host made alone."""
        if self._lease is not None and not self.host.lease_held:
            self._withdraw("host revoked lease")
            if self.state in (LinkState.TYPE111_NEGOTIATED, LinkState.STREAMING):
                self.state = LinkState.CARPLAY_ACTIVE

    def _run_closers_only(self, closers: dict[str, Callable[[], None]] | None) -> None:
        """Refused negotiation: release what the caller already acquired."""
        for name, close in (closers or {}).items():
            self._closers.append(_Closer(name, close))
        self._withdraw("negotiation refused: CarPlay not active")

    def _withdraw(self, reason: str) -> CleanupReport:
        revoke_error: Exception | None = None
        try:
            self.host.revoke(reason)  # visible content first
        except Exception as exc:  # noqa: BLE001 - a host that cannot confirm must not skip cleanup
            revoke_error = exc
        self._lease = None
        closers, self._closers = self._closers[::-1], []
        ran: list[str] = []
        failed: list[str] = []
        for closer in closers:  # independent: one failure never stops the rest
            try:
                closer.close()
                ran.append(closer.name)
            except Exception:  # noqa: BLE001 - cleanup must continue
                failed.append(closer.name)
        report = CleanupReport(reason, tuple(ran), tuple(failed))
        self.reports.append(report)
        if revoke_error is not None:
            raise revoke_error  # reported, after every independent closer has run
        return report
