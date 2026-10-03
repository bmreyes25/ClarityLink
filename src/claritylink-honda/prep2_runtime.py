"""Offline PREP2 policy, attachment, restoration and experiment models."""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


STOCK_CALLSITE = bytes.fromhex("fe f7 d1 ff")
JMCS_SHA256 = "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
EXPECTED_ARCH = ("ELF32", "ARM", "little-endian", "EABI5", "Thumb")
CALLER_CONTEXT_SHA256 = "edec335f1cd6f9d0d053a0d2b4a05f515c25e1a1524fccca2c4c0ebd610273df"
CALLER_PROLOGUE_SHA256 = "be9f272a09201f326e42c27962609add81149bbe1adb9e843bb8b8ff685d7878"


class AttachState(str, Enum):
    DISABLED = "DISABLED"
    TARGET_FINGERPRINT_VERIFIED = "TARGET_FINGERPRINT_VERIFIED"
    ORIGINAL_CALLSITE_VERIFIED = "ORIGINAL_CALLSITE_VERIFIED"
    ATTACHMENT_PREPARED = "ATTACHMENT_PREPARED"
    ATTACHMENT_ACTIVE = "ATTACHMENT_ACTIVE"
    ATTACHMENT_VERIFIED = "ATTACHMENT_VERIFIED"
    BOUNDED_TEST_ACTIVE = "BOUNDED_TEST_ACTIVE"
    DETACH_REQUESTED = "DETACH_REQUESTED"
    RESTORE_COMPARE_VERIFIED = "RESTORE_COMPARE_VERIFIED"
    ORIGINAL_BYTES_RESTORED = "ORIGINAL_BYTES_RESTORED"
    RESTORATION_VERIFIED = "RESTORATION_VERIFIED"
    REBOOT_REQUIRED = "REBOOT_REQUIRED"
    POST_REBOOT_STOCK_VERIFIED = "POST_REBOOT_STOCK_VERIFIED"
    ABORT_WITHOUT_WRITE = "ABORT_WITHOUT_WRITE"
    ATTACHMENT_FAILED = "ATTACHMENT_FAILED"


class SimMemory:
    """Byte-array simulation only. No process/device backend exists."""
    def __init__(self, code: bytes = STOCK_CALLSITE, fail_at: str | None = None) -> None:
        self.code, self.fail_at = bytearray(code), fail_at
        self.writes = 0
        self.cache_syncs = 0
        self.read_only = True

    def install(self, expected: bytes, project_form: bytes) -> bool:
        if bytes(self.code) != expected or self.fail_at == "before_install": return False
        if self.fail_at == "make_writable": return False
        self.read_only = False
        if bytes(self.code) != expected:
            self.read_only = True; return False
        self.code[:] = project_form; self.writes += 1; self.cache_syncs += 1
        if self.fail_at == "restore_protection": return False
        self.read_only = True
        return self.fail_at != "install_verify" and bytes(self.code) == project_form

    def restore(self, expected_project: bytes, stock: bytes) -> bool:
        if bytes(self.code) != expected_project: return False
        if self.fail_at == "make_writable": return False
        self.read_only = False
        if bytes(self.code) != expected_project:
            self.read_only = True; return False
        self.code[:] = stock; self.writes += 1; self.cache_syncs += 1
        if self.fail_at == "restore_protection": return False
        self.read_only = True
        return self.fail_at != "restore_verify" and bytes(self.code) == stock


@dataclass
class AttachmentModel:
    jmcs_sha256: str = JMCS_SHA256
    architecture: tuple[str, ...] = EXPECTED_ARCH
    callsite: bytes = STOCK_CALLSITE
    bl_target: int = 0x289F60
    continuation: int = 0x28AFBE
    caller_context_sha256: str = CALLER_CONTEXT_SHA256
    caller_prologue_sha256: str = CALLER_PROLOGUE_SHA256
    project_form: bytes = b"CLAB"  # inert non-instruction token; never a vehicle patch
    memory: SimMemory = field(default_factory=SimMemory)
    state: AttachState = AttachState.DISABLED
    lease_active: bool = False
    generation_active: bool = False
    listener_active: bool = False
    accepted_fd_active: bool = False
    worker_active: bool = False
    bridge_active: bool = False
    type111_work_active: bool = False
    cleanup_log: list[str] = field(default_factory=list)
    failure: str | None = None

    def attach(self) -> bool:
        if self.state is not AttachState.DISABLED:
            self.failure = "already_attached_or_busy"
            return False
        exact = (self.jmcs_sha256 == JMCS_SHA256 and self.architecture == EXPECTED_ARCH and
                 self.callsite == STOCK_CALLSITE and self.bl_target == 0x289F60 and
                 self.continuation == 0x28AFBE and
                 self.caller_context_sha256 == CALLER_CONTEXT_SHA256 and
                 self.caller_prologue_sha256 == CALLER_PROLOGUE_SHA256)
        if not exact or bytes(self.memory.code) != self.callsite:
            self.state = AttachState.ABORT_WITHOUT_WRITE; self.failure = "compatibility_gate"
            return False
        self.state = AttachState.TARGET_FINGERPRINT_VERIFIED
        self.state = AttachState.ORIGINAL_CALLSITE_VERIFIED
        self.state = AttachState.ATTACHMENT_PREPARED
        if not self.memory.install(STOCK_CALLSITE, self.project_form):
            self.failure = "install_verification_failed"
            if bytes(self.memory.code) == self.project_form:
                restored = self.memory.restore(self.project_form, STOCK_CALLSITE)
                self.state = AttachState.ATTACHMENT_FAILED if restored else AttachState.REBOOT_REQUIRED
            else:
                self.state = AttachState.ABORT_WITHOUT_WRITE
            return False
        self.state = AttachState.ATTACHMENT_ACTIVE
        if bytes(self.memory.code) != self.project_form:
            self.failure = "attachment_verify_failed"; return False
        self.state = AttachState.ATTACHMENT_VERIFIED
        self.lease_active = True
        return True

    def bounded_test(self) -> bool:
        if self.state is not AttachState.ATTACHMENT_VERIFIED or not self.lease_active:
            return False
        self.state = AttachState.BOUNDED_TEST_ACTIVE
        return True

    def detach(self, *, cleanup_ok: bool = True, fail_at: str | None = None) -> bool:
        if self.state is AttachState.RESTORATION_VERIFIED:
            return bytes(self.memory.code) == STOCK_CALLSITE and not any((
                self.generation_active, self.listener_active, self.accepted_fd_active,
                self.worker_active, self.bridge_active, self.lease_active))
        if self.state is AttachState.ATTACHMENT_FAILED:
            return bytes(self.memory.code) == STOCK_CALLSITE and self.memory.read_only
        if self.state is AttachState.REBOOT_REQUIRED:
            return False
        if self.state is AttachState.DISABLED:
            return True
        self.state = AttachState.DETACH_REQUESTED
        self.lease_active = False
        # Reverse ownership order; every resource flag remains visible on failure.
        cleanup = (
            ("stop_type111_work", "type111_work_active"),
            ("retire_generation", "generation_active"),
            ("close_accepted_fd", "accepted_fd_active"),
            ("close_listener", "listener_active"),
            ("join_worker", "worker_active"),
            ("disable_bridge", "bridge_active"),
        )
        if not cleanup_ok and fail_at is None: fail_at = "stop_type111_work"
        for operation, field_name in cleanup:
            if fail_at == operation:
                self.failure = f"{operation}_failed"
                return False
            self.cleanup_log.append(operation)
            setattr(self, field_name, False)
        if bytes(self.memory.code) != self.project_form:
            self.failure = "installed_bytes_mismatch"; self.state = AttachState.ABORT_WITHOUT_WRITE
            return False
        self.state = AttachState.RESTORE_COMPARE_VERIFIED
        if not self.memory.restore(self.project_form, STOCK_CALLSITE):
            self.failure = "restore_verification_failed"; return False
        self.state = AttachState.ORIGINAL_BYTES_RESTORED
        self.state = AttachState.RESTORATION_VERIFIED
        return True

    def lease_expired(self) -> bool:
        self.lease_active = False
        return self.detach()


class RestoreState(str, Enum):
    RESTORED_TO_VERIFIED_STOCK = "RESTORED_TO_VERIFIED_STOCK"
    RESTORATION_NOT_PROVEN = "RESTORATION_NOT_PROVEN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class RestorationFacts:
    callsite: bytes | None
    surrounding_context_matches: bool
    bl_target: int | None
    continuation: int | None
    generation_absent: bool
    listener_absent: bool
    accepted_fd_absent: bool
    worker_absent: bool
    bridge_inactive: bool
    fresh: bool = True
    applicable: bool = True


def verify_restoration(facts: RestorationFacts) -> RestoreState:
    if not isinstance(facts, RestorationFacts):
        return RestoreState.RESTORATION_NOT_PROVEN
    if facts.applicable is False:
        return RestoreState.NOT_APPLICABLE
    exact = (facts.applicable is True and facts.fresh is True and facts.callsite == STOCK_CALLSITE and
             facts.surrounding_context_matches is True and facts.bl_target == 0x289F60 and
             facts.continuation == 0x28AFBE and facts.generation_absent is True and
             facts.listener_absent is True and facts.accepted_fd_absent is True and
             facts.worker_absent is True and facts.bridge_inactive is True)
    return RestoreState.RESTORED_TO_VERIFIED_STOCK if exact else RestoreState.RESTORATION_NOT_PROVEN


class PolicyResult(str, Enum):
    BIND_POLICY_READY = "BIND_POLICY_READY"
    BIND_POLICY_PARTIAL = "BIND_POLICY_PARTIAL"
    BIND_POLICY_REJECTED = "BIND_POLICY_REJECTED"


@dataclass(frozen=True)
class NetworkEvidence:
    capture_classification: str = "UNRESOLVED"
    candidate_interface: str | None = None
    candidate_address: str | None = None
    address_family: str | None = None
    prefix: int | None = None
    scope_id: str | int | None = None
    route_interface: str | None = None
    interface_scope_id: int | None = None
    route_supported: bool = False
    phase_reversal_supported: bool = False
    evidence_class: str = "UNRESOLVED"
    competing_candidates: int = 0
    wildcard_requested: bool = False
    stale: bool = False
    traffic_only: bool = False


@dataclass(frozen=True)
class HondaBindingPolicy:
    interface: str
    address: str
    family: int
    scope_id: str | int | None
    classification: str = "HONDA_OBSERVED_POLICY"


def evaluate_binding(e: NetworkEvidence) -> tuple[PolicyResult, HondaBindingPolicy | None, str]:
    if not isinstance(e, NetworkEvidence):
        return PolicyResult.BIND_POLICY_REJECTED, None, "evidence_record_invalid"
    if e.wildcard_requested: return PolicyResult.BIND_POLICY_REJECTED, None, "wildcard_prohibited"
    if e.stale or e.capture_classification in ("INVALID", "PARTIAL") or e.traffic_only:
        return PolicyResult.BIND_POLICY_REJECTED, None, "insufficient_or_stale_evidence"
    if e.evidence_class in ("LAB_SYNTHETIC_CONFIRMED", "SYNTHETIC_TEST_VALUE", "HOST_ONLY_OBSERVED"):
        return PolicyResult.BIND_POLICY_REJECTED, None, "synthetic_evidence_cannot_authorize_honda_bind"
    if (isinstance(e.competing_candidates, bool) or not isinstance(e.competing_candidates, int) or
            not 0 <= e.competing_candidates <= 1):
        return PolicyResult.BIND_POLICY_REJECTED, None, "competing_candidates"
    placeholders = (None, "", "UNKNOWN", "UNRESOLVED", "FROM_43T0D_EVIDENCE")
    if (e.capture_classification == "UNRESOLVED" or e.candidate_interface in placeholders or
            e.candidate_address in placeholders or e.address_family in placeholders):
        return PolicyResult.BIND_POLICY_PARTIAL, None, "43t0d_placeholders_unresolved"
    if e.capture_classification != "COMPLETE":
        return PolicyResult.BIND_POLICY_REJECTED, None, "capture_not_complete"
    if e.evidence_class != "HONDA_CONFIRMED":
        return PolicyResult.BIND_POLICY_REJECTED, None, "evidence_class_not_authoritative"
    if (not isinstance(e.candidate_interface, str) or not isinstance(e.candidate_address, str) or
            not isinstance(e.address_family, str) or
            (e.scope_id is not None and (isinstance(e.scope_id, bool) or not isinstance(e.scope_id, (int, str))))):
        return PolicyResult.BIND_POLICY_REJECTED, None, "evidence_field_type_invalid"
    if isinstance(e.prefix, bool) or not isinstance(e.prefix, int):
        return PolicyResult.BIND_POLICY_REJECTED, None, "prefix_missing"
    if "%" in e.candidate_address:
        return PolicyResult.BIND_POLICY_REJECTED, None, "scope_must_be_separate_from_address"
    try:
        iface = ipaddress.ip_interface(f"{e.candidate_address}/{e.prefix}")
    except ValueError:
        return PolicyResult.BIND_POLICY_REJECTED, None, "invalid_address_or_prefix"
    addr = iface.ip
    expected_family = "IPv4" if addr.version == 4 else "IPv6"
    if e.address_family != expected_family:
        return PolicyResult.BIND_POLICY_REJECTED, None, "family_mismatch"
    if addr.is_unspecified or addr.is_multicast or addr.is_loopback:
        return PolicyResult.BIND_POLICY_REJECTED, None, "non_unicast_address"
    scope = e.scope_id
    if isinstance(addr, ipaddress.IPv6Address) and addr.is_link_local:
        scope_matches = ((isinstance(scope, str) and scope == e.candidate_interface) or
                         (isinstance(scope, int) and not isinstance(scope, bool) and
                          scope > 0 and isinstance(e.interface_scope_id, int) and
                          not isinstance(e.interface_scope_id, bool) and
                          e.interface_scope_id > 0 and scope == e.interface_scope_id))
        if not scope_matches:
            return PolicyResult.BIND_POLICY_REJECTED, None, "link_local_scope_required_or_mismatched"
    elif scope is not None:
        return PolicyResult.BIND_POLICY_REJECTED, None, "unexpected_scope_for_non_link_local_address"
    if e.route_supported is not True or e.route_interface != e.candidate_interface:
        return PolicyResult.BIND_POLICY_REJECTED, None, "route_interface_mismatch_or_missing"
    if e.phase_reversal_supported is not True:
        return PolicyResult.BIND_POLICY_REJECTED, None, "phase_reversal_not_supported"
    return PolicyResult.BIND_POLICY_READY, HondaBindingPolicy(e.candidate_interface, str(addr), addr.version, scope), "specific_address_only"


class ExperimentState(str, Enum):
    IDLE = "IDLE"
    STOCK_BASELINE_VERIFIED = "STOCK_BASELINE_VERIFIED"
    ATTACHMENT_VERIFIED = "ATTACHMENT_VERIFIED"
    WAITING_FOR_SETUP = "WAITING_FOR_SETUP"
    TYPE111_REQUEST_OBSERVED = "TYPE111_REQUEST_OBSERVED"
    LISTENER_PREPARED = "LISTENER_PREPARED"
    RESPONSE_EXTENSION_PREPARED = "RESPONSE_EXTENSION_PREPARED"
    STOCK_SERIALIZER_CALLED = "STOCK_SERIALIZER_CALLED"
    LOCAL_SERIALIZER_SUCCESS = "LOCAL_SERIALIZER_SUCCESS"
    WAITING_FOR_PHONE_CONNECT = "WAITING_FOR_PHONE_CONNECT"
    PHONE_CONNECTED = "PHONE_CONNECTED"
    FIRST_BYTES_CAPTURED = "FIRST_BYTES_CAPTURED"
    TYPE111_GENERATION_RETIRED = "TYPE111_GENERATION_RETIRED"
    DETACH_STARTED = "DETACH_STARTED"
    RESTORATION_VERIFIED = "RESTORATION_VERIFIED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class NegotiationController:
    """Event-gated synthetic controller. No implicit retries or live backend."""
    MAX_CONNECTION_ATTEMPTS = 1
    MAX_FIRST_BYTES = 256
    MAX_ACCEPT_WAIT_SECONDS = 2.0
    MAX_FIRST_BYTE_WAIT_SECONDS = 0.25
    MAX_EXPERIMENT_SECONDS = 5.0  # synthetic watchdog budget; not a Honda timing claim
    ORDER = [ExperimentState.STOCK_BASELINE_VERIFIED, ExperimentState.ATTACHMENT_VERIFIED,
             ExperimentState.WAITING_FOR_SETUP, ExperimentState.TYPE111_REQUEST_OBSERVED,
             ExperimentState.LISTENER_PREPARED, ExperimentState.RESPONSE_EXTENSION_PREPARED,
             ExperimentState.STOCK_SERIALIZER_CALLED, ExperimentState.LOCAL_SERIALIZER_SUCCESS,
             ExperimentState.WAITING_FOR_PHONE_CONNECT, ExperimentState.PHONE_CONNECTED,
             ExperimentState.FIRST_BYTES_CAPTURED, ExperimentState.TYPE111_GENERATION_RETIRED,
             ExperimentState.DETACH_STARTED, ExperimentState.RESTORATION_VERIFIED,
             ExperimentState.COMPLETE]

    def __init__(self) -> None:
        self.state = ExperimentState.IDLE
        self.type110_owned = False
        self.type110_closed = False
        self.audio_changed = False
        self.center_display_changed = False
        self.failure: str | None = None
        self.events: list[ExperimentState] = []
        self.phone_connections = 0
        self.first_bytes: bytes | None = None
        self.elapsed_seconds = 0.0

    def advance(self, state: ExperimentState, *, local_serializer_ok: bool | None = None,
                elapsed_seconds: float = 0.0) -> None:
        if state not in self.ORDER or (self.ORDER.index(state) != self.ORDER.index(self.state) + 1 if self.state in self.ORDER else state is not self.ORDER[0]):
            self.state = ExperimentState.FAILED; self.failure = "invalid_transition"; raise ValueError(self.failure)
        import math
        if (isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)) or
                not math.isfinite(elapsed_seconds) or elapsed_seconds < 0):
            self.abort("invalid_elapsed_time")
        self.elapsed_seconds += elapsed_seconds
        if self.elapsed_seconds > self.MAX_EXPERIMENT_SECONDS:
            self.abort("experiment_deadline_exceeded")
        if state is ExperimentState.LOCAL_SERIALIZER_SUCCESS and local_serializer_ok is not True:
            self.state = ExperimentState.FAILED; self.failure = "serializer_not_successful"; raise ValueError(self.failure)
        if state is ExperimentState.PHONE_CONNECTED and self.phone_connections != 1:
            self.abort("phone_connection_evidence_missing")
        if state is ExperimentState.FIRST_BYTES_CAPTURED and not self.first_bytes:
            self.abort("first_byte_evidence_missing")
        self.state = state; self.events.append(state)
        if self.type110_owned or self.type110_closed or self.audio_changed or self.center_display_changed:
            self.state = ExperimentState.FAILED; self.failure = "type110_invariant_broken"; raise ValueError(self.failure)

    def record_phone_connection(self, *, elapsed_seconds: float = 0.0) -> None:
        if self.state is not ExperimentState.WAITING_FOR_PHONE_CONNECT:
            self.abort("connection_before_wait_state")
        import math
        if (isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)) or
                not math.isfinite(elapsed_seconds) or not 0 <= elapsed_seconds <= self.MAX_ACCEPT_WAIT_SECONDS):
            self.abort("phone_connect_timeout_or_invalid_elapsed")
        self.elapsed_seconds += elapsed_seconds
        if self.elapsed_seconds > self.MAX_EXPERIMENT_SECONDS:
            self.abort("experiment_deadline_exceeded")
        self.phone_connections += 1
        if self.phone_connections > self.MAX_CONNECTION_ATTEMPTS:
            self.abort("connection_attempt_limit_exceeded")

    def capture_first_bytes(self, data: bytes, *, elapsed_seconds: float = 0.0) -> bytes:
        if self.state is not ExperimentState.PHONE_CONNECTED:
            self.abort("capture_before_connection")
        if self.first_bytes is not None:
            self.abort("duplicate_first_byte_capture")
        if not isinstance(data, bytes) or not data or len(data) > self.MAX_FIRST_BYTES:
            self.abort("first_bytes_invalid_or_over_limit")
        import math
        if (isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)) or
                not math.isfinite(elapsed_seconds) or
                not 0 <= elapsed_seconds <= self.MAX_FIRST_BYTE_WAIT_SECONDS):
            self.abort("first_byte_timeout_or_invalid_elapsed")
        self.elapsed_seconds += elapsed_seconds
        if self.elapsed_seconds > self.MAX_EXPERIMENT_SECONDS:
            self.abort("experiment_deadline_exceeded")
        self.first_bytes = bytes(data)
        return self.first_bytes

    def abort(self, reason: str) -> None:
        self.state = ExperimentState.FAILED
        self.failure = reason
        raise ValueError(reason)


class PrefixClass(str, Enum):
    LEGACY_SCREENSTREAM_CANDIDATE = "LEGACY_SCREENSTREAM_CANDIDATE"
    MODERN_CHACHA_SCREEN_CANDIDATE = "MODERN_CHACHA_SCREEN_CANDIDATE"
    CLEAR_OR_UNKNOWN = "CLEAR_OR_UNKNOWN"
    MALFORMED = "MALFORMED"
    UNSUPPORTED = "UNSUPPORTED"


MAX_PREFIX_CAPTURE_BYTES = 256


@dataclass(frozen=True)
class PrefixResult:
    classification: PrefixClass
    reasons: tuple[str, ...]
    bytes_observed_count: int
    crypto_branch_selected: bool = False
    required_next_evidence: str = "Honda framing/security evidence"


def classify_type111_prefix(data: bytes, *, max_bytes: int = 256, source_class: str = "UNKNOWN") -> PrefixResult:
    """Structural only: never decrypt, infer security mode, or expose payload."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= MAX_PREFIX_CAPTURE_BYTES:
        return PrefixResult(PrefixClass.UNSUPPORTED, ("invalid_or_unbounded_capture_limit",), 0)
    if not isinstance(data, bytes):
        return PrefixResult(PrefixClass.MALFORMED, ("input_not_bytes",), 0)
    if len(data) > max_bytes:
        return PrefixResult(PrefixClass.MALFORMED, ("prefix_exceeds_bound",), min(len(data), max_bytes))
    if not data:
        return PrefixResult(PrefixClass.CLEAR_OR_UNKNOWN, ("zero_bytes",), 0)
    if len(data) < 128:
        return PrefixResult(PrefixClass.CLEAR_OR_UNKNOWN, ("truncated_before_known_128_byte_envelope",), len(data))
    body_len = int.from_bytes(data[:4], "little")
    opcode = data[4]
    if body_len > 16 * 1024 * 1024:
        return PrefixResult(PrefixClass.MALFORMED, ("declared_length_exceeds_local_bound",), len(data))
    if opcode == 0:
        return PrefixResult(PrefixClass.MALFORMED, ("impossible_zero_opcode_candidate",), len(data))
    if source_class == "HONDA_TYPE110_FIXTURE":
        if opcode not in (0, 1, 2, 4, 5):
            return PrefixResult(PrefixClass.UNSUPPORTED, ("opcode_not_in_honda_type110_static_set",), len(data))
        return PrefixResult(PrefixClass.LEGACY_SCREENSTREAM_CANDIDATE,
                            ("known_honda_type110_128_byte_header_shape", "candidate_only"), len(data))
    if source_class == "PLAYPORT_MODERN_FIXTURE":
        # Provenance can annotate a fixture, but the shared header does not
        # distinguish legacy AES from modern ChaCha; no crypto label follows.
        return PrefixResult(PrefixClass.CLEAR_OR_UNKNOWN,
                            ("external_playport_fixture_provenance_only", "header_not_crypto_discriminator"), len(data))
    if body_len == 0 and len(data) > 128:
        return PrefixResult(PrefixClass.MALFORMED, ("length_inconsistent_with_prefix",), len(data))
    if opcode not in (0, 1, 2, 4, 5):
        return PrefixResult(PrefixClass.UNSUPPORTED, ("opcode_outside_known_structural_set",), len(data))
    return PrefixResult(PrefixClass.CLEAR_OR_UNKNOWN, ("unknown_structural_candidate",), len(data))
