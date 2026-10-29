"""Host-owned Display 1 expiry timer (CL-INT-04). Original, offline, synthetic-only.

``Display1LeaseHost`` (CL-INT-03) expires leases lazily, on the next read. That is
not enough when the only reader is the producer: a dead producer never reads. This
service gives the host its OWN clock-driven thread that calls
``Display1LeaseHost.enforce_expiry`` so content is withdrawn when the lease runs
out whether or not any producer ``tick()``, heartbeat or cleanup callback ever
arrives. The service lives in the host process; it imports nothing from the
producer side.

  * The watchdog never dies silently: an unexpected exception is counted, recorded
    and retried on the next wake-up, and ``status().watchdog_alive`` says so.
  * A failed cluster withdrawal is reported (``withdrawal_pending``) and retried on
    every wake-up. Grants are refused while it is pending.
  * ``stop()`` is idempotent, joins the watchdog, withdraws, and says whether the
    thread really ended. Restart is a new instance (new epoch), never a reuse.

Not evidence about a Honda or a vehicle. ``safe_for_honda()`` stays False.
"""
from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import failsafe_coordinator as fsc  # noqa: E402

WATCHDOG_MAX_WAIT_SECONDS = 0.05  # upper bound on any sleep: a heartbeat can move the deadline
WATCHDOG_JOIN_SECONDS = 2.0
WATCHDOG_ERROR_LOG_LIMIT = 32  # bounded diagnostics


@dataclass(frozen=True)
class HostStatus:
    epoch: int
    lease_held: bool
    visible: bool
    withdrawal_pending: bool
    residual: int
    revocations: tuple[str, ...]  # bounded: newest DIAGNOSTIC_LOG_LIMIT entries
    withdrawal_failures: tuple[str, ...]  # bounded likewise
    revocation_count: int
    withdrawal_failure_count: int
    watchdog_alive: bool
    watchdog_errors: int
    watchdog_enforcements: int


class Display1HostService:
    """Owns one ``Display1LeaseHost`` and the timer that enforces its expiry."""

    def __init__(self, host: fsc.Display1LeaseHost | None = None, *,
                 max_wait: float = WATCHDOG_MAX_WAIT_SECONDS) -> None:
        if max_wait <= 0:
            raise ValueError("max_wait must be positive")
        self.host = host if host is not None else fsc.Display1LeaseHost()
        self._max_wait = max_wait
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None
        self._state_lock = threading.Lock()
        self._errors = 0
        self._enforcements = 0
        self.error_types: list[str] = []

    # ---- lifecycle ----
    def start(self) -> None:
        with self._state_lock:
            if self._stopping.is_set():
                raise RuntimeError("service was stopped; create a new instance (new epoch)")
            if self._thread is not None:
                return
            thread = threading.Thread(target=self._run, name="Display1HostWatchdog", daemon=True)
            self._thread = thread
        thread.start()

    def stop(self) -> bool:
        """Stop the timer and withdraw. True only if the thread ended and nothing is left."""
        self._stopping.set()
        self._wake.set()
        with self._state_lock:
            thread = self._thread
        ended = True
        if thread is not None and thread is not threading.current_thread():
            thread.join(WATCHDOG_JOIN_SECONDS)
            ended = not thread.is_alive()
        try:
            self.host.revoke("host service stopped")
        except Exception as exc:  # noqa: BLE001 - a withdrawal failure is also in the host's state
            self._record_error(exc)
        return ended and not self.host.withdrawal_pending and not self.host.residual_state

    def poke(self) -> None:
        """Wake the watchdog now (new deadline, test hook). Never required for safety."""
        self._wake.set()

    # ---- the timer ----
    def _run(self) -> None:
        while not self._stopping.is_set():
            self._enforce_once()
            self._wake.wait(self._next_wait())
            self._wake.clear()
        self._enforce_once()

    def _enforce_once(self) -> None:
        try:
            if self.host.enforce_expiry():
                with self._state_lock:
                    self._enforcements += 1
        except Exception as exc:  # noqa: BLE001 - a dead timer is a silent hole; count and retry
            self._record_error(exc)

    def _record_error(self, exc: Exception) -> None:
        with self._state_lock:
            self._errors += 1
            if len(self.error_types) < WATCHDOG_ERROR_LOG_LIMIT:
                self.error_types.append(type(exc).__name__)

    def _next_wait(self) -> float:
        try:
            deadline = self.host.next_deadline()
            if deadline is None:
                return self._max_wait
            return min(max(deadline - self.host.now(), 0.0), self._max_wait)
        except Exception:  # noqa: BLE001 - fall back to the bounded poll
            return self._max_wait

    # ---- reporting ----
    def status(self) -> HostStatus:
        host = self.host
        try:
            held, visible = host.lease_held, host.visible_content is not None
        except Exception:  # noqa: BLE001 - an unreadable host is reported, not hidden
            held, visible = host.withdrawal_pending, host.withdrawal_pending
        thread = self._thread
        with self._state_lock:
            errors, enforcements = self._errors, self._enforcements
        return HostStatus(
            epoch=host.epoch, lease_held=held, visible=visible,
            withdrawal_pending=host.withdrawal_pending, residual=len(host.residual_state),
            revocations=tuple(host.revocations), withdrawal_failures=tuple(host.withdrawal_failures),
            revocation_count=host.revocation_count,
            withdrawal_failure_count=host.withdrawal_failure_count,
            watchdog_alive=bool(thread is not None and thread.is_alive()),
            watchdog_errors=errors, watchdog_enforcements=enforcements,
        )

    def revoke_if_current(self, lease: fsc.LeaseGrant, reason: str) -> bool:
        """Revoke only if ``lease`` is still current: a stale owner's death cannot hit a newer lease."""
        return self.host.revoke_if_current(lease, reason)
