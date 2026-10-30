"""CL-T111-EPHEMERAL-HARNESS-01: deterministic offline cleanup/recovery state machine.

Evidence scope: SYNTHETIC/MODEL only (label ``SYN``). Everything here runs on the development
host against the existing CL-INT-04 stack (``Display1LeaseHost`` / ``Display1HostService`` /
``Display1HostServer`` / ``RemoteDisplay1Host`` / ``FailSafeCoordinator``). There is NO second
Display 1 lease system: leases, epochs, generations, connection-bound revocation and host-owned
expiry are exactly the CL-INT-04 ones.

Nothing here touches a Honda, a vehicle, ADB or a connected iPhone, and no outcome claims Honda
cleanup, RAM-backed target storage, restoration or reboot recovery. ``safe_for_honda()`` is False
and the deployment status is ``VEHICLE_DEPLOYMENT_NOT_AUTHORIZED``. The inventory of what the
harness owns, and every UNKNOWN Honda-dependent property, is ``ephemeral_harness_manifest.json``.

Rules the state machine enforces:
  * A resource that is missing or unreachable is UNKNOWN, never proof of a clean state.
  * An unreachable host or severed control connection is UNKNOWN, never "withdrawn".
  * A simulated reboot restarts the modelled host (new epoch) and wipes only the directory the
    model labels volatile. It is a model assumption and proves nothing about any target.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

import display1_host_ipc as ipc
import display1_host_service as svc
import failsafe_coordinator as fsc

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).with_name("ephemeral_harness_manifest.json")
EVIDENCE_LABEL = "SYN"
DEPLOYMENT_STATUS = "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED"
SECTIONS = ("files", "processes", "sockets", "services", "mounts", "display1_leases",
            "cleanup_obligations")
STORAGE_CLASSES = ("RAM_BACKED_VOLATILE", "PERSISTENT_DATA", "UNKNOWN_PLATFORM")
LEASE_SECONDS = 1.0
WATCHDOG_MAX_WAIT = 0.005
CLEANUP_BOUND_SECONDS = 5.0  # generous ceiling; every wait returns as soon as its condition holds
POLL_SECONDS = 0.005
BASE_EPOCH = 7000  # deterministic epochs: boot N has epoch BASE_EPOCH + N
PRODUCER_FRAMES = 3
LATE_SEQUENCE = 99
PROBE_GENERATION = 1
LEASE_EXPIRY_MULTIPLE = 3  # silent-producer fault advances the clock this many leases


class ManifestError(ValueError):
    """The manifest promotes a property it has no evidence for, or is malformed."""


class HarnessStateError(RuntimeError):
    """An operation is not legal in the harness's current state."""


class HarnessFault(str, Enum):
    NORMAL_TERMINATION = "NORMAL_TERMINATION"
    PROCESS_CRASH = "PROCESS_CRASH"
    LOST_PRODUCER = "LOST_PRODUCER"
    LOST_CONTROL_CONNECTION = "LOST_CONTROL_CONNECTION"
    INTERRUPTED_CLEANUP = "INTERRUPTED_CLEANUP"
    HOST_RESTART = "HOST_RESTART"
    SIMULATED_REBOOT = "SIMULATED_REBOOT"
    MISSING_CLEANUP_RESOURCE = "MISSING_CLEANUP_RESOURCE"


class HarnessState(str, Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    FAULTED = "FAULTED"
    CLEANING = "CLEANING"
    CLEAN_MODEL = "CLEAN_MODEL"  # clean in the model only; see NoTargetClaims
    CLEANUP_INCOMPLETE = "CLEANUP_INCOMPLETE"


_TRANSITIONS = {
    HarnessState.IDLE: {HarnessState.ACTIVE},
    HarnessState.ACTIVE: {HarnessState.FAULTED},
    HarnessState.FAULTED: {HarnessState.CLEANING},
    HarnessState.CLEANING: {HarnessState.CLEAN_MODEL, HarnessState.CLEANUP_INCOMPLETE},
    HarnessState.CLEANUP_INCOMPLETE: {HarnessState.CLEANING},
    HarnessState.CLEAN_MODEL: {HarnessState.ACTIVE},
}


class ObligationStatus(str, Enum):
    PENDING = "PENDING"
    CLEARED_MODEL = "CLEARED_MODEL"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NoTargetClaims:
    """Constant negative claims carried by every outcome. Nothing in the harness sets one True."""

    honda_cleanup_established: bool = False
    ram_backed_target_storage_established: bool = False
    restoration_established: bool = False
    reboot_recovery_established: bool = False
    safe_for_honda: bool = False
    deployment_status: str = DEPLOYMENT_STATUS


NO_TARGET_CLAIMS = NoTargetClaims()


@dataclass(frozen=True)
class CleanupOutcome:
    fault: HarnessFault | None
    state: HarnessState
    obligations: Mapping[str, ObligationStatus]
    stale_lease_withdrawn: bool | None  # None = could not be confirmed
    stale_lease_fenced: bool | None  # None = not applicable / not checked
    detail: tuple[str, ...]
    evidence_label: str = EVIDENCE_LABEL
    claims: NoTargetClaims = NO_TARGET_CLAIMS

    @property
    def clean(self) -> bool:
        return self.state is HarnessState.CLEAN_MODEL


# ---- manifest ----
def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest


def _entries(manifest: Mapping[str, Any]):
    for section in SECTIONS:
        for entry in manifest.get(section, ()):
            yield section, entry


def validate_manifest(manifest: Mapping[str, Any], *, root: Path = ROOT) -> None:
    """Reject a manifest that promotes a Honda-dependent property without cited existing evidence."""
    if manifest.get("safe_for_honda") is not False:
        raise ManifestError("safe_for_honda must be false")
    if manifest.get("deployment_status") != DEPLOYMENT_STATUS:
        raise ManifestError("deployment_status must be VEHICLE_DEPLOYMENT_NOT_AUTHORIZED")
    if manifest.get("evidence_label") != EVIDENCE_LABEL:
        raise ManifestError("evidence_label must be SYN")
    claims = manifest.get("claims")
    if not isinstance(claims, dict) or not claims or any(v is not False for v in claims.values()):
        raise ManifestError("every target claim must be explicitly false")
    classes = manifest.get("storage_classes", {})
    if set(classes) != set(STORAGE_CLASSES):
        raise ManifestError("storage_classes must separate exactly " + ", ".join(STORAGE_CLASSES))
    for name, info in classes.items():
        if info.get("target_established") is not False or info.get("target_status") != "UNKNOWN":
            raise ManifestError(f"storage class {name} must be target UNKNOWN")
    unknowns = {u.get("id"): u for u in manifest.get("platform_unknowns", ())}
    tmp = unknowns.get("data_local_tmp_reboot_volatility")
    if tmp is None or tmp.get("status") != "UNKNOWN" or tmp.get("evidence"):
        raise ManifestError("/data/local/tmp reboot volatility must be UNKNOWN with no evidence")
    for unknown in unknowns.values():
        if unknown.get("status") != "UNKNOWN" or unknown.get("evidence"):
            raise ManifestError(f"platform unknown {unknown.get('id')} must stay UNKNOWN with no evidence")
    for section, entry in _entries(manifest):
        _validate_entry(section, entry, root)
    modelled = {e["id"] for e in manifest["cleanup_obligations"]
                if e.get("enforced_by") == "state_machine"}
    if modelled != set(OBLIGATION_ORDER):
        raise ManifestError("state-machine obligations must match the harness handlers")


def _validate_entry(section: str, entry: Mapping[str, Any], root: Path) -> None:
    ident = entry.get("id", "?")
    scope, status = entry.get("scope"), entry.get("status")
    dependent = entry.get("honda_dependent")
    if scope not in ("SYNTHETIC_HOST_MODEL", "HONDA_TARGET") or type(dependent) is not bool:
        raise ManifestError(f"{section}/{ident}: scope and honda_dependent are required")
    if scope == "HONDA_TARGET" and not dependent:
        raise ManifestError(f"{section}/{ident}: a target property is Honda-dependent")
    if entry.get("storage_class") not in STORAGE_CLASSES + ("NOT_APPLICABLE",):
        raise ManifestError(f"{section}/{ident}: unknown storage class")
    evidence = entry.get("evidence", [])
    if dependent and (status != "UNKNOWN" or evidence):
        raise ManifestError(
            f"{section}/{ident}: a Honda-dependent property must stay UNKNOWN with no cited evidence")
    for cited in evidence:
        if not (root / cited).is_file():
            raise ManifestError(f"{section}/{ident}: cited evidence {cited} does not exist")


# ---- synthetic producer ----
class ManualClock:
    """Deterministic host clock for lease expiry; the host never reads wall time here."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class Producer:
    """A synthetic producer: the real ``FailSafeCoordinator`` over a real host connection."""

    remote: ipc.RemoteDisplay1Host
    coordinator: fsc.FailSafeCoordinator

    @property
    def lease(self) -> fsc.LeaseGrant | None:
        return self.coordinator.lease


# ---- cleanup obligations ----
OBLIGATION_ORDER = (
    "producer_connection_closed",
    "display1_lease_withdrawn",
    "persistent_marker_removed",
    "unknown_class_marker_removed",
    "volatile_marker_removed",
)
_FILE_OBLIGATIONS = {
    "persistent_marker_removed": ("persistent", "stage.marker"),
    "unknown_class_marker_removed": ("unknown", "scratch.marker"),
    "volatile_marker_removed": ("volatile", "producer.pid"),
}
_MODEL_DIRS = ("volatile", "persistent", "unknown")


@dataclass
class _Boot:
    """One modelled boot of the host: a service and its socket server."""

    number: int
    service: svc.Display1HostService
    server: ipc.Display1HostServer


class EphemeralHarness:
    def __init__(self, *, lease_seconds: float = LEASE_SECONDS,
                 cleanup_bound: float = CLEANUP_BOUND_SECONDS,
                 inject_withdraw_failures: int = 0, lab_controls: bool = False) -> None:
        self.manifest = load_manifest()
        self.lease_seconds = lease_seconds
        self.cleanup_bound = cleanup_bound
        self._inject_failures = inject_withdraw_failures
        self._lab_controls = lab_controls  # opt-in: the ingest pipeline's select_page is a lab op
        self.state = HarnessState.IDLE
        self.clock = ManualClock()
        self.producer: Producer | None = None
        self.control: ipc.RemoteDisplay1Host | None = None
        self._root: Path | None = None
        self._boot: _Boot | None = None
        self._ledger: dict[str, ObligationStatus] = {}
        self._stale_lease: fsc.LeaseGrant | None = None
        self._fault: HarnessFault | None = None
        self._detail: tuple[str, ...] = ()
        self._fenced: bool | None = None
        self.boots = 0

    # ---- lifecycle ----
    @property
    def socket_path(self) -> str:
        assert self._root is not None
        return str(self._root / "h.sock")

    @property
    def host(self) -> fsc.Display1LeaseHost:
        assert self._boot is not None
        return self._boot.service.host

    def path_of(self, obligation: str) -> Path:
        directory, name = _FILE_OBLIGATIONS[obligation]
        assert self._root is not None
        return self._root / directory / name

    def start(self) -> None:
        self._require(HarnessState.IDLE)
        self._root = Path(tempfile.mkdtemp(prefix="clhz", dir="/tmp"))  # short: AF_UNIX path limit
        for name in _MODEL_DIRS:
            (self._root / name).mkdir()
        self._ledger = {key: ObligationStatus.PENDING for key in OBLIGATION_ORDER}
        for obligation in _FILE_OBLIGATIONS:
            self.path_of(obligation).write_text("synthetic\n", encoding="utf-8")
        self._start_boot()
        self._transition(HarnessState.ACTIVE)

    def _start_boot(self) -> None:
        self.boots += 1
        host = fsc.Display1LeaseHost(lease_seconds=self.lease_seconds, clock=self.clock,
                                     epoch=BASE_EPOCH + self.boots)
        host.select_page(True)
        self._inject_withdraw_failures(host)
        service = svc.Display1HostService(host, max_wait=WATCHDOG_MAX_WAIT)
        server = ipc.Display1HostServer(service, self.socket_path, lab_controls=self._lab_controls)
        server.start()
        self._boot = _Boot(self.boots, service, server)
        self.control = ipc.RemoteDisplay1Host(self.socket_path)

    def _inject_withdraw_failures(self, host: fsc.Display1LeaseHost) -> None:
        if not self._inject_failures:
            return
        cluster = host._cluster  # noqa: SLF001 - the lab seam the CL-INT-04 tests use
        real, left = cluster.withdraw_main, [self._inject_failures]

        def flaky() -> None:
            if left[0]:
                left[0] -= 1
                raise OSError("synthetic cluster refused")
            real()

        cluster.withdraw_main = flaky

    def attach_producer(self) -> Producer:
        self._require(HarnessState.ACTIVE)
        if self.producer is not None:
            raise HarnessStateError("a producer is already attached")
        remote = ipc.RemoteDisplay1Host(self.socket_path)
        coordinator = fsc.FailSafeCoordinator(remote)
        coordinator.phone_attached()
        coordinator.carplay_started()
        if not coordinator.type111_negotiated():
            remote.close()
            raise HarnessStateError("synthetic negotiation refused")
        for index in range(PRODUCER_FRAMES):
            if coordinator.submit_frame(f"synthetic-frame-{index}") is not fsc.SubmitResult.ACCEPTED:
                remote.close()
                raise HarnessStateError("synthetic frame refused")
        self.producer = Producer(remote, coordinator)
        return self.producer

    def close(self) -> bool:
        """Release the harness's own host-side scratch. True only if every thread and the socket ended."""
        clean = True
        for client in (self.producer.remote if self.producer else None, self.control):
            if client is not None:
                client.close()
        if self._boot is not None:
            clean = self._boot.server.stop() and not os.path.exists(self.socket_path)
            self._boot = None
        if self._root is not None:
            shutil.rmtree(self._root, ignore_errors=True)
            self._root = None
        return clean

    # ---- state machine ----
    def _require(self, *allowed: HarnessState) -> None:
        if self.state not in allowed:
            raise HarnessStateError(f"illegal in state {self.state.value}")

    def _transition(self, target: HarnessState) -> None:
        if target not in _TRANSITIONS[self.state]:
            raise HarnessStateError(f"illegal transition {self.state.value} -> {target.value}")
        self.state = target

    def _set(self, obligation: str, status: ObligationStatus) -> None:
        self._ledger = {**self._ledger, obligation: status}  # new mapping, never mutated in place

    # ---- faults ----
    def inject(self, fault: HarnessFault, *, max_steps: int | None = None) -> CleanupOutcome:
        """Apply one fault, then run cleanup. INTERRUPTED_CLEANUP stops cleanup after one step;
        ``max_steps`` interrupts any other fault's cleanup after that many obligations."""
        self._require(HarnessState.ACTIVE)
        if self.producer is None:
            raise HarnessStateError("attach a producer first")
        self._fault, self._detail, self._fenced = fault, (), None
        self._stale_lease = self.producer.lease
        self._transition(HarnessState.FAULTED)
        _FAULT_ACTIONS[fault](self)
        if max_steps is None and fault is HarnessFault.INTERRUPTED_CLEANUP:
            max_steps = 1
        return self.recover(max_steps=max_steps)

    def _terminate_normally(self) -> None:
        assert self.producer is not None
        self.producer.coordinator.fault(fsc.Fault.CARPLAY_ENDED)
        self.producer.remote.close()

    def _crash_producer(self) -> None:
        assert self.producer is not None
        self.producer.remote.close()  # no coordinator cleanup: the host sees the connection end

    def _lose_producer(self) -> None:
        """Producer alive but silent: only the host-owned timer, driven by the manual clock, can act."""
        assert self._boot is not None
        self.clock.advance(self.lease_seconds * LEASE_EXPIRY_MULTIPLE)
        self._boot.service.poke()
        self._await_timer_withdrawal()

    def _await_timer_withdrawal(self) -> None:
        """Wait, producer socket still open, for the host timer to drop the lease (bounded)."""
        assert self._boot is not None
        deadline = time.monotonic() + self.cleanup_bound
        while time.monotonic() < deadline:
            # Read only the timer-owned counter here. Calling control.status() can ask the
            # model host to expire lazily and would make this test pass without the watchdog.
            if self._boot.service.watchdog_enforcements > 0:
                return
            time.sleep(POLL_SECONDS)
        raise HarnessStateError("host timer did not enforce producer expiry within the cleanup bound")

    def _lose_control_connection(self) -> None:
        assert self.control is not None
        self.control.close()
        self._detail += ("control connection severed; host state is unobservable",)

    def _restart_host(self) -> None:
        old = self._boot
        assert old is not None
        self._detail += (f"host stopped clean={old.server.stop()}",)
        self._start_boot()
        stale = self._stale_lease
        if stale is not None:
            self._fenced = self._probe_epoch_fence(stale)

    def _probe_epoch_fence(self, stale: fsc.LeaseGrant) -> bool:
        """A boot holding no lease answers REJECTED_NO_LEASE before it compares epochs, so the epoch
        fence is only observable while the new boot holds a lease. Grant a probe lease, check the
        previous boot's lease fails on epoch, then revoke the probe so the boot is left clean."""
        granted, probe = self.host.grant_above(PROBE_GENERATION)
        if granted is not fsc.GrantResult.GRANTED or probe is None:
            return False
        try:
            return self.host.submit(stale, LATE_SEQUENCE, "late") is fsc.SubmitResult.REJECTED_EPOCH
        finally:
            self.host.revoke("harness epoch probe")

    def _simulate_reboot(self) -> None:
        """Restart the modelled host and wipe ONLY the directory the model labels volatile."""
        self._restart_host()
        assert self._root is not None
        volatile = self._root / "volatile"
        shutil.rmtree(volatile, ignore_errors=True)
        volatile.mkdir()
        self._set("volatile_marker_removed", ObligationStatus.CLEARED_MODEL)
        self._detail += ("simulated reboot: model wiped its volatile directory only",
                         "simulated reboot is a model assumption; no target behavior observed")

    def _remove_resource_out_of_band(self) -> None:
        self.path_of("persistent_marker_removed").unlink()
        self._crash_producer()
        self._detail += ("a recorded cleanup resource vanished before cleanup",)

    # ---- recovery ----
    def recover(self, *, max_steps: int | None = None) -> CleanupOutcome:
        """Run pending cleanup obligations in order; resumable after interruption or an unknown."""
        self._require(HarnessState.FAULTED, HarnessState.CLEANUP_INCOMPLETE)
        self._transition(HarnessState.CLEANING)
        steps = 0
        for obligation in OBLIGATION_ORDER:
            if self._ledger[obligation] is ObligationStatus.CLEARED_MODEL:
                continue
            if max_steps is not None and steps >= max_steps:
                self._detail += ("cleanup interrupted before all obligations ran",)
                break
            steps += 1
            self._set(obligation, self._run_obligation(obligation))
        done = all(s is ObligationStatus.CLEARED_MODEL for s in self._ledger.values())
        self._transition(HarnessState.CLEAN_MODEL if done else HarnessState.CLEANUP_INCOMPLETE)
        return self._outcome()

    def _run_obligation(self, obligation: str) -> ObligationStatus:
        if obligation == "producer_connection_closed":
            return self._close_producer()
        if obligation == "display1_lease_withdrawn":
            return self._confirm_lease_withdrawn()
        return self._remove_file(obligation)

    def _close_producer(self) -> ObligationStatus:
        if self.producer is not None:
            self.producer.remote.close()
            if self.producer.remote.connected:
                return ObligationStatus.FAILED
        return ObligationStatus.CLEARED_MODEL

    def _remove_file(self, obligation: str) -> ObligationStatus:
        path = self.path_of(obligation)
        if not path.exists():
            # Absent could mean "removed" or "never there": this harness did not remove it, so unknown.
            self._detail += (f"{obligation}: resource missing; cleanup unverifiable",)
            return ObligationStatus.UNKNOWN
        try:
            path.unlink()
        except OSError:
            return ObligationStatus.FAILED
        return ObligationStatus.FAILED if path.exists() else ObligationStatus.CLEARED_MODEL

    def _confirm_lease_withdrawn(self) -> ObligationStatus:
        verdict = self._lease_withdrawn()
        if verdict is None:
            self._detail += ("host state unobservable; withdrawal unconfirmed",)
            return ObligationStatus.UNKNOWN
        return ObligationStatus.CLEARED_MODEL if verdict else ObligationStatus.FAILED

    def _lease_withdrawn(self) -> bool | None:
        """True/False from the host's own report within the bound; None if it cannot be asked."""
        control = self.control
        if control is None or not control.connected:
            return None
        deadline = time.monotonic() + self.cleanup_bound
        while True:
            try:
                status = control.status()
            except ipc.HostIpcError:
                return None
            if not (status["lease_held"] or status["visible"] or status["residual"]
                    or status["withdrawal_pending"]):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(POLL_SECONDS)

    def reconnect_control(self) -> None:
        """Re-open the harness's own control connection (it never owned the producer's lease)."""
        if self.control is not None:
            self.control.close()
        self.control = ipc.RemoteDisplay1Host(self.socket_path)

    def _outcome(self) -> CleanupOutcome:
        lease = self._ledger["display1_lease_withdrawn"]
        withdrawn = {ObligationStatus.CLEARED_MODEL: True, ObligationStatus.FAILED: False}.get(lease)
        return CleanupOutcome(
            fault=self._fault, state=self.state, obligations=dict(self._ledger),
            stale_lease_withdrawn=withdrawn, stale_lease_fenced=self._fenced,
            detail=self._detail)


_FAULT_ACTIONS: dict[HarnessFault, Callable[[EphemeralHarness], None]] = {
    HarnessFault.NORMAL_TERMINATION: EphemeralHarness._terminate_normally,
    HarnessFault.PROCESS_CRASH: EphemeralHarness._crash_producer,
    HarnessFault.LOST_PRODUCER: EphemeralHarness._lose_producer,
    HarnessFault.LOST_CONTROL_CONNECTION: EphemeralHarness._lose_control_connection,
    HarnessFault.INTERRUPTED_CLEANUP: EphemeralHarness._crash_producer,
    HarnessFault.HOST_RESTART: EphemeralHarness._restart_host,
    HarnessFault.SIMULATED_REBOOT: EphemeralHarness._simulate_reboot,
    HarnessFault.MISSING_CLEANUP_RESOURCE: EphemeralHarness._remove_resource_out_of_band,
}
