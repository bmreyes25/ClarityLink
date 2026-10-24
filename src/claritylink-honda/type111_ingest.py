"""Offline Type111 ingest -> decode -> lease-gated simulated Display 1 (CL-T111-INGEST-01).

Wires the EXISTING ``claritylink_jmcs.Receiver`` (Type111 framing, security
provider, AVCC handling, FFmpeg decoder, per-stream dispatcher) to the
EXISTING CL-INT-03 ``FailSafeCoordinator`` / ``Display1LeaseHost``. No frame
reaches the simulated host except through a lease-bound submit.

  receiver (framing -> unprotect -> avcC/Annex-B -> FFmpeg PNG)
    -> dispatcher worker -> LeaseGatedOutput.show
    -> png_to_rgb24 -> VideoFrame -> LeaseBoundFrame
    -> FailSafeCoordinator.submit_frame -> Display1LeaseHost -> SimulatedClusterHost

Scope and limits (not evidence about a Honda or an iPhone):
  * Input is locally generated, clear, lab-framed H.264 (SYNTHETIC_LAB_CONTENT).
    The CURRENT_IOS_TYPE111 profile is a lab framing hypothesis, not proof of
    the real iPhone wire format; no real iPhone-origin bytes are processed.
  * ``lab_mode=False`` refuses to run: synthetic authentication and clear media
    can never stand in for production evidence.
  * Control-thread API (open/setup/pump/tick/fault) is single-threaded; the only
    other thread is the receiver's dispatcher worker, inside ``pump_frame``.
  * Lease expiry is evaluated lazily by the host and adopted here by ``tick()``
    in THIS process. A dead producer cannot run ``tick()``: guaranteed
    withdrawal then needs a host-owned timer (CL-INT-04, still open).
  * ``safe_for_honda()`` stays False; nothing here touches a vehicle.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import sys
import threading
from time import monotonic, perf_counter
from typing import Any, Callable

_HERE = Path(__file__).resolve().parent
for _path in (_HERE, _HERE.parent / "claritylink-jmcs"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import failsafe_coordinator as fsc  # noqa: E402
from claritylink_jmcs.decoder import DecodedFrame  # noqa: E402
from claritylink_jmcs.display import DisplayError, NullDisplay  # noqa: E402
from claritylink_jmcs.frames import FrameError, Provenance, VideoFrame, png_to_rgb24  # noqa: E402
from claritylink_jmcs.media import FramingProfile  # noqa: E402
from claritylink_jmcs.receiver import Receiver, ReceiverError, ReceiverState  # noqa: E402
from claritylink_jmcs.stream_dispatch import StreamIdentity  # noqa: E402

Fault = fsc.Fault
SECONDARY_STREAM = 111
# Owned by the pipeline: letting a caller override them would defeat lab-mode gating.
RESERVED_RECEIVER_OPTIONS = frozenset({"clear_lab", "display", "primary_display", "framing_profile"})
_FULL_TEARDOWN = (Fault.USB_UNPLUG, Fault.CARPLAY_ENDED, Fault.RECEIVER_DEATH)
_SNAPSHOT_FIELDS = ("sessions", "primary_listeners", "secondary_listeners", "security_contexts",
                    "decoders", "displayed_frames", "display_uncleared")
CONVERT_SAMPLES = 256  # bounded timing history


class IngestError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---- fault classification ---------------------------------------------------
# The receiver tears down the secondary stream on EVERY media-path error except a
# stale decoder, so any error outside FRAME_ONLY_CODES ends the Type111 lease.
# Session-staleness and identity errors are NOT frame-only: the receiver either
# tore the stream down (identity) or the session is already gone, so the lease
# must be withdrawn with it.
FRAME_ONLY_CODES = frozenset({
    "stale_secondary_decoder",      # a superseded decoder lost a race; stream is fine
})
DECODER_CODES = frozenset({
    "decode_failed", "decoder_closed", "invalid_access_unit", "invalid_output_dimensions",
    "invalid_decoded_dimensions", "secondary_decoder_restart_failed",
})
# Everything else (socket EOF/read failure, malformed framing/AVCC, security
# refusal, display/lease refusal) is a Type111 transport/stream failure.


def classify_receiver_code(code: str) -> Fault | None:
    """Fault to raise for a receiver error code; None = reject the frame only."""
    if code in FRAME_ONLY_CODES:
        return None
    if code in DECODER_CODES:
        return Fault.DECODER_DEATH
    return Fault.TYPE111_TRANSPORT_FAILURE


@dataclass(frozen=True)
class LeaseBoundFrame:
    """What the host holds: the frame plus the lease/sequence it was submitted under."""

    frame: VideoFrame
    lease_epoch: int
    lease_generation: int
    sequence: int


@dataclass(frozen=True)
class IngestOutcome:
    accepted: bool
    code: str | None = None
    fault: Fault | None = None
    frame: LeaseBoundFrame | None = None


@dataclass(frozen=True)
class FaultRecord:
    kind: Fault | None  # None: host-side revocation adopted (expiry / no progress)
    code: str
    report: fsc.CleanupReport
    cleanup_ok: bool = True  # False: receiver-side cleanup left something behind (see cleanup_failures)


class LeaseGatedOutput:
    """``FrameOutput`` sink: decoded PNG in, lease-bound RGB24 out. Fails closed."""

    def __init__(self, coordinator: fsc.FailSafeCoordinator, *, lab_mode: bool) -> None:
        self._coordinator = coordinator
        self._lab_mode = lab_mode
        self._lock = threading.RLock()
        self._local = threading.local()
        self._identity: StreamIdentity | None = None
        self._active = False
        self._last_timestamp = -1
        self.accepted = 0
        self.rejected: list[str] = []
        self.last_bound: LeaseBoundFrame | None = None
        self.convert_seconds: deque[float] = deque(maxlen=CONVERT_SAMPLES)

    def activate(self, identity: StreamIdentity) -> None:
        with self._lock:
            self._identity, self._active, self._last_timestamp = identity, True, -1

    def deactivate(self) -> None:
        with self._lock:
            self._active = False

    def inside_show(self) -> bool:
        return bool(getattr(self._local, "in_show", False))

    def fail_closed(self, reason: str) -> None:
        """Stop accepting frames and hide host content now (safe direction)."""
        with self._lock:
            self._active = False
            self.last_bound = None
            self._coordinator.host.revoke(reason)

    def _reject(self, code: str) -> DisplayError:
        self.rejected.append(code)
        self.fail_closed(code)
        return DisplayError(code)

    def show(self, frame: DecodedFrame) -> None:
        with self._lock:  # cheap admission checks first
            if not self._lab_mode:
                raise self._reject("lab_mode_required")
            identity = self._identity
            if not self._active or identity is None:
                raise self._reject("output_inactive")
            if frame.generation != identity.stream_generation:
                raise self._reject("stale_stream_generation")
        started = perf_counter()  # the slow conversion runs without holding the lock
        try:
            width, height, pixels = png_to_rgb24(frame.png)
            if (frame.width, frame.height) != (width, height):
                raise FrameError("decoder_dimension_mismatch")
        except FrameError as exc:
            raise self._reject(exc.code) from exc
        converted = perf_counter() - started
        with self._lock:
            if not self._active or self._identity is not identity:  # revoked while converting
                raise self._reject("output_inactive")
            try:
                if frame.timestamp < self._last_timestamp:
                    raise FrameError("timestamp_regression")
                lease = self._coordinator.lease
                if lease is None:
                    raise FrameError("lease_rejected:REJECTED_NO_LEASE")
                video = VideoFrame(pixels, width, height, width * 3, frame.timestamp,
                                   identity.session_generation, identity.stream_type,
                                   identity.connection_id, identity.stream_generation,
                                   Provenance.SYNTHETIC_LAB_CONTENT)
            except FrameError as exc:
                raise self._reject(exc.code) from exc
            self.convert_seconds.append(converted)
            bound = LeaseBoundFrame(video, lease.epoch, lease.generation, self._coordinator.sequence)
            self._local.in_show = True
            try:
                result = self._coordinator.submit_frame(bound)
            finally:
                self._local.in_show = False
            if result is not fsc.SubmitResult.ACCEPTED:
                raise self._reject(f"lease_rejected:{result.value}")
            self._last_timestamp = frame.timestamp
            self.accepted += 1
            self.last_bound = bound

    def clear(self) -> None:
        """Receiver/dispatcher cleanup: withdraw host content; idempotent."""
        with self._lock:
            self._active = False
            self.last_bound = None
            self._coordinator.host.revoke("type111 output cleared")


class Type111IngestPipeline:
    """Owns one Receiver, one coordinator and the bridge between their lifecycles."""

    def __init__(self, *, lab_mode: bool, clock: Callable[[], float] = monotonic,
                 lease_seconds: float = fsc.DEFAULT_LEASE_SECONDS,
                 frame_age_limit: float | None = None,
                 primary_display: Any = None,
                 receiver_kwargs: dict[str, Any] | None = None) -> None:
        kwargs = dict(receiver_kwargs or {})
        if RESERVED_RECEIVER_OPTIONS & kwargs.keys():
            raise IngestError("reserved_receiver_option")
        self.lab_mode = lab_mode
        self.host = fsc.Display1LeaseHost(lease_seconds=lease_seconds, clock=clock,
                                          frame_age_limit=frame_age_limit)
        self.coordinator = fsc.FailSafeCoordinator(self.host)
        self.output = LeaseGatedOutput(self.coordinator, lab_mode=lab_mode)
        self.primary_display = primary_display if primary_display is not None else NullDisplay()
        self.receiver = Receiver(clear_lab=lab_mode, display=self.output,
                                 primary_display=self.primary_display,
                                 framing_profile=FramingProfile.CURRENT_IOS_TYPE111, **kwargs)
        self.generation = 0
        self.faults: list[FaultRecord] = []
        self.cleanup_failures: list[str] = []
        self._cleanup_deferred = False

    # ---- session lifecycle ----
    def open_session(self) -> int:
        if not self.lab_mode:
            raise IngestError("lab_mode_required")
        generation = self.receiver.start_session()
        self.receiver.info_exchanged(generation)
        self.generation = generation
        self.coordinator.phone_attached()
        self.coordinator.carplay_started()
        return generation

    def setup_primary(self, stream_connection_id: int) -> bool:
        """Synthetic Type110 on the (separate) primary output."""
        self.receiver.setup({"streams": [{"type": 110, "streamConnectionID": stream_connection_id}]},
                            self.generation)
        return self.receiver.primary is not None

    def setup_type111(self, stream_connection_id: int) -> IngestOutcome:
        self.settle()  # adopt an expiry the host already applied before judging "active"
        if self.receiver.secondary is not None or self.coordinator.lease is not None:
            return IngestOutcome(False, "type111_already_active")  # never disturbs the live stream
        try:
            self.receiver.setup({"streams": [{"type": 111, "streamConnectionID": stream_connection_id}]},
                                self.generation)
        except ReceiverError as exc:
            return self._init_failed(exc.code)
        if self.receiver.secondary is None:  # receiver rolled back and kept only Type110
            return self._init_failed("type111_setup_refused")
        identity = self.receiver.stream_identity(SECONDARY_STREAM)
        self._cleanup_deferred = False
        negotiated = self.coordinator.type111_negotiated(
            {"receiver_secondary": self._close_secondary, "output": self.output.deactivate})
        if not negotiated:  # the coordinator already ran the closers; finish and record, never raise
            cleaned = self._finalize(None)
            self.faults.append(FaultRecord(None, "negotiation_refused", self.coordinator.reports[-1], cleaned))
            return IngestOutcome(False, "negotiation_refused", None)
        self.output.activate(identity)
        self.host.select_page(True)
        return IngestOutcome(True)

    def _init_failed(self, code: str) -> IngestOutcome:
        self._fault(Fault.INIT_FAILURE, code)
        return IngestOutcome(False, code, Fault.INIT_FAILURE)

    def accept_type111(self, timeout: float = 1.0) -> None:
        self.receiver.accept_secondary(self.generation, timeout)

    # ---- data path ----
    def pump_frame(self) -> IngestOutcome:
        """Read and present one Type111 message through the real receiver."""
        before = self.output.accepted
        try:
            data = self.receiver.receive_secondary_frame(self.generation)
        except ReceiverError as exc:
            return self._failed(exc.code, classify_receiver_code(exc.code))
        except Exception as exc:  # noqa: BLE001 - an unexpected receiver failure is a death, not a frame error
            return self._failed(f"receiver_exception:{type(exc).__name__}", Fault.RECEIVER_DEATH)
        if self.settle():  # the lease went away while this frame was in flight
            return IngestOutcome(False, "lease_revoked_during_frame", None)
        if self.output.accepted > before:
            return IngestOutcome(True, frame=self.output.last_bound)
        if data == b"":
            return IngestOutcome(True)  # VideoConfig message: nothing to present
        return self._failed("frame_not_presented", Fault.TYPE111_TRANSPORT_FAILURE)

    def _failed(self, code: str, kind: Fault | None) -> IngestOutcome:
        if kind is None:
            self.settle()  # drain any cleanup deferred while the worker was inside show()
            return IngestOutcome(False, code, None)
        self._fault(kind, code)
        return IngestOutcome(False, code, kind)

    # ---- liveness ----
    def heartbeat(self) -> bool:
        alive = self.coordinator.heartbeat()
        if not alive:
            self.settle()
        return alive

    def tick(self) -> bool:
        """Adopt a host-side revocation (expiry, no frame progress). True if it acted."""
        return self.settle()

    def settle(self) -> bool:
        """Reconcile coordinator and receiver with whatever the host already revoked."""
        if self.coordinator.lease is None or self.host.lease_held:
            if self._cleanup_deferred:
                self._finalize(None)
            return False
        self.output.deactivate()
        reason = self.host.revocations[-1] if self.host.revocations else "host revoked lease"
        self.coordinator.sync()
        report = self.coordinator.reports[-1]
        self.faults.append(FaultRecord(None, reason, report, self._finalize(None)))
        return True

    # ---- faults ----
    def disconnect(self, kind: Fault = Fault.CARPLAY_ENDED) -> fsc.CleanupReport:
        """Normal or unexpected phone/CarPlay loss; tears the whole receiver session down."""
        return self._fault(kind, "disconnect")

    def end_type111(self) -> fsc.CleanupReport:
        """Orderly end of only the secondary stream; CarPlay and Type110 stay up."""
        return self._fault(Fault.TYPE111_TRANSPORT_FAILURE, "type111_ended")

    def factory_interrupt(self) -> fsc.CleanupReport:
        return self._fault(Fault.FACTORY_WARNING, "factory_interrupt")

    def clear_factory_interrupt(self) -> None:
        self.host.clear_interrupt()

    def display_restart(self) -> fsc.CleanupReport:
        return self._fault(Fault.DISPLAY_HOST_RESTART, "display_host_restart")

    def _fault(self, kind: Fault, code: str) -> fsc.CleanupReport:
        self.output.fail_closed(code)  # visible content first, before any cleanup
        report = self.coordinator.fault(kind)
        self.faults.append(FaultRecord(kind, code, report, self._finalize(kind)))
        return report

    def _finalize(self, kind: Fault | None) -> bool:
        """Idempotently finish receiver cleanup the coordinator could not do inline.

        Returns False (and records the cause in ``cleanup_failures``) when anything
        project-owned is still held afterwards; it never raises.
        """
        self._cleanup_deferred = False
        try:
            if kind in _FULL_TEARDOWN:
                self.receiver.teardown(self.generation)
                leftovers = self.session_residual()
                if leftovers:
                    raise IngestError("session_cleanup_incomplete:" + ",".join(leftovers))
            else:
                self._close_secondary()
        except Exception as exc:  # noqa: BLE001 - cleanup failure is recorded, never raised
            self.cleanup_failures.append(getattr(exc, "code", type(exc).__name__))
            return False
        return True

    def _close_secondary(self) -> None:
        if self.output.inside_show():  # on the dispatcher worker: cannot join itself
            self._cleanup_deferred = True  # surfaced by residual() until settle() drains it
            return
        self.output.deactivate()
        self.receiver.teardown_secondary(self.generation)
        if (self.receiver.secondary or self.receiver.decoder or self.receiver.security
                or self.receiver.display_uncleared
                or SECONDARY_STREAM in self.receiver.dispatch_registry_snapshot()):
            raise IngestError("secondary_cleanup_incomplete")

    # ---- inspection ----
    def residual(self) -> tuple[str, ...]:
        """Everything project-owned still held for Type111 (empty when clean)."""
        held: list[str] = [f"host:{type(item).__name__}" for item in self.host.residual_state]
        held += [name for name, value in (("listener", self.receiver.secondary),
                                          ("decoder", self.receiver.decoder),
                                          ("security", self.receiver.security),
                                          ("display_frame", self.output.last_bound),
                                          ("display_uncleared", self.receiver.display_uncleared),
                                          ("cleanup_deferred", self._cleanup_deferred))
                 if value]
        if SECONDARY_STREAM in self.receiver.dispatch_registry_snapshot():
            held.append("dispatcher")
        return tuple(held)

    def session_residual(self) -> tuple[str, ...]:
        """Whole-session leftovers (both streams, authority session); empty after a full teardown."""
        snapshot = self.receiver.snapshot()
        held = [name for name in _SNAPSHOT_FIELDS if getattr(snapshot, name)]
        if self.receiver.state is ReceiverState.FAILED:
            held.append("state_failed")
        return tuple(held)
