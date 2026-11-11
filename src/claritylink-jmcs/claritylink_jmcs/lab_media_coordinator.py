"""Join the synthetic Type111 negotiation model to the existing lab ingest path.

This coordinator creates no decoder or listener. It drives an injected
``Type111IngestPipeline`` (which owns its loopback listener, FFmpeg decoder,
lease and Display 1 sink) only after the model's stock-first SETUP has created
the child. Model listener reservations and the receiver's bound socket are
separate resources with separate identities.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping

from .lab_dual_display import (
    InfoPolicy, LabDualDisplayModel, ModelInfoResult, ModelSetupResult,
)
from .session_transport import ControlRequest, TransportError, validate_control_request
from legacy_dual_screen_twin import DuplicateStreamConnectionID
from type111_setup_contract import (
    SerializerResult, SetupContractError, parse_setup_request,
)


class LabMediaError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SetupOrder(str, Enum):
    TYPE110_FIRST = "type110_first"
    TYPE111_FIRST = "type111_first"


@dataclass(frozen=True)
class ComponentIdentity:
    """Explicit cross-component identity map; fields are never numerically aliased."""

    parent_identity: object
    parent_generation: int
    child_generation: int
    stream_connection_id: int
    receiver_session_generation: int
    receiver_stream_generation: int
    decoder_generation: "DecoderGenerationIdentity | None" = None
    display_lease_epoch: int | None = None
    display_lease_generation: int | None = None


@dataclass(frozen=True)
class DecoderGenerationIdentity:
    """Decoder epoch paired with its receiver session, distinct from stream epoch."""

    receiver_session_generation: int
    restart_ordinal: int


@dataclass(frozen=True)
class IntegratedSetupResult:
    info: ModelInfoResult
    model_setup: ModelSetupResult
    type110_ready: bool
    type111_ready: bool
    identity: ComponentIdentity | None
    error_code: str | None


class _IngestChildLease:
    """Generation-bound project resource owned by one negotiated model child."""

    def __init__(self, ingest: Any, receiver_generation: int) -> None:
        self._ingest = ingest
        self._receiver_generation = receiver_generation
        self._closed = False
        self.close_count = 0

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.close_count += 1
        # A delayed B1 cleanup must not tear down the pipeline after B2 has
        # opened a newer receiver generation on the same injected pipeline.
        if self._ingest.generation == self._receiver_generation:
            self._ingest.end_type111()


class NegotiatedType111MediaSession:
    """Coordinate LAB-01 negotiation with the existing receiver/decoder path.

    A session instance is single-use. Reconnects use a fresh model/session and
    may reuse the ingest pipeline after its prior parent has been closed.
    """

    def __init__(self, model: LabDualDisplayModel, ingest: Any) -> None:
        if not isinstance(model, LabDualDisplayModel):
            raise LabMediaError("lab_dual_display_model_required")
        if ingest is None or not callable(getattr(ingest, "open_session", None)):
            raise LabMediaError("existing_ingest_pipeline_required")
        self.model = model
        self.ingest = ingest
        self._lock = RLock()
        self._parent_identity: object | None = None
        self._parent_generation: int | None = None
        self._receiver_generation: int | None = None
        self._info: ModelInfoResult | None = None
        self._child_lease: _IngestChildLease | None = None
        self._identity: ComponentIdentity | None = None
        self._closed = False
        self._setup_done = False

    @property
    def identity(self) -> ComponentIdentity | None:
        with self._lock:
            return self._identity

    @property
    def active(self) -> bool:
        with self._lock:
            return (not self._closed and self._parent_identity is not None and
                    self._parent_generation is not None)

    def open(
        self,
        parent_identity: object,
        parent_generation: int,
        *,
        info_policy: InfoPolicy = InfoPolicy.DISABLED,
    ) -> ModelInfoResult:
        with self._lock:
            if self._parent_identity is not None or self._closed:
                raise LabMediaError("integrated_session_is_single_use")
            self.model.open(parent_identity, parent_generation)
            self._parent_identity = parent_identity
            self._parent_generation = parent_generation
            try:
                self._receiver_generation = self.ingest.open_session()
                self._info = self.model.get_info(
                    parent_identity, parent_generation, policy=info_policy
                )
                return self._info
            except Exception:
                try:
                    self.model.close_parent(parent_identity, parent_generation)
                finally:
                    if self._receiver_generation is not None:
                        self.ingest.disconnect()
                    self._closed = True
                raise

    def setup(
        self,
        request: Mapping[str, Any],
        serializer: Callable[[Mapping[str, Any]], SerializerResult],
        *,
        order: SetupOrder = SetupOrder.TYPE110_FIRST,
    ) -> IntegratedSetupResult:
        with self._lock:
            self._require_open()
            if self._info is None:
                raise LabMediaError("info_exchange_required")
            if self._setup_done:
                raise LabMediaError("setup_already_completed")
            if not isinstance(order, SetupOrder) or not callable(serializer):
                raise LabMediaError("setup_order_or_serializer_invalid")
            receiver_generation = self._receiver_generation
            assert receiver_generation is not None
            try:
                validate_control_request(
                    ControlRequest("SETUP", "/session", request, receiver_generation),
                    receiver_generation,
                )
                streams = request.get("streams")
                if not isinstance(streams, (list, tuple)) or len(streams) > 16:
                    raise TransportError("setup_stream_count_limit")
                parsed = parse_setup_request(request)
            except (TransportError, SetupContractError, DuplicateStreamConnectionID,
                    AttributeError, TypeError) as exc:
                # Preserve the mock parent's stock path for malformed input;
                # no media receiver or child is allocated on this branch.
                model_setup = self.model.handle_setup(
                    self._parent_identity, self._parent_generation or 0,
                    request, serializer,
                )
                self._setup_done = True
                return IntegratedSetupResult(
                    self._info, model_setup, False, False, None,
                    getattr(exc, "code", "invalid_setup_request"),
                )
            primary_ids = [item.stream_connection_id for item in parsed
                           if item.stream_type == 110]
            secondary_ids = [item.stream_connection_id for item in parsed
                             if item.stream_type == 111]
            if len(primary_ids) > 1 or len(secondary_ids) > 1:
                model_setup = self.model.handle_setup(
                    self._parent_identity, self._parent_generation or 0,
                    request, serializer,
                )
                self._setup_done = True
                return IntegratedSetupResult(
                    self._info, model_setup, False, False, None,
                    model_setup.error_code or "duplicate_stream_type",
                )
            if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
                   for value in primary_ids + secondary_ids):
                model_setup = self.model.handle_setup(
                    self._parent_identity, self._parent_generation or 0,
                    request, serializer,
                )
                self._setup_done = True
                return IntegratedSetupResult(
                    self._info, model_setup, False, False, None,
                    model_setup.error_code or "invalid_stream_connection_id",
                )
            if primary_ids and secondary_ids and primary_ids[0] == secondary_ids[0]:
                model_setup = self.model.handle_setup(
                    self._parent_identity, self._parent_generation or 0,
                    request, serializer,
                )
                self._setup_done = True
                return IntegratedSetupResult(
                    self._info, model_setup, False, False, None,
                    model_setup.error_code or "duplicate_stream_connection_id",
                )

            primary_ready = self.ingest.receiver.primary is not None
            secondary_ready = False
            error_code: str | None = None
            if secondary_ids and not primary_ids and not primary_ready:
                error_code = "type110_parent_required"
            if primary_ids and not primary_ready:
                try:
                    primary_ready = bool(self.ingest.setup_primary(primary_ids[0]))
                except Exception:
                    primary_ready = False
                if not primary_ready:
                    error_code = "type110_receiver_setup_failed"
            elif (primary_ids and self.ingest.receiver.primary_id is not None and
                  self.ingest.receiver.primary_id != primary_ids[0]):
                raise LabMediaError("type110_connection_id_mismatch")

            def prepare_actual_child(candidate: Mapping[str, Any]) -> SerializerResult:
                nonlocal secondary_ready, error_code
                candidate_streams = candidate.get("streams")
                has_child = (isinstance(candidate_streams, (list, tuple)) and any(
                    isinstance(item, Mapping) and item.get("type") == 111
                    for item in candidate_streams
                ))
                if not has_child:
                    return serializer(candidate)
                if (not secondary_ids or not self._info or
                        not self._info.type111_candidate_present or
                        not primary_ready):
                    error_code = error_code or "negotiated_child_prerequisite_missing"
                    return SerializerResult(0, 1)
                outcome = self.ingest.setup_type111(secondary_ids[0])
                secondary_ready = bool(
                    outcome.accepted and self.ingest.receiver.secondary is not None and
                    self.ingest.receiver.decoder is not None and
                    self.ingest.receiver.security is not None and
                    self.ingest.coordinator.lease is not None
                )
                if not secondary_ready:
                    error_code = outcome.code or "lab_receiver_not_ready"
                    return SerializerResult(0, 1)
                child = self.model.delegator.secondary.lifecycle.current_type111
                if child is None:
                    self.ingest.end_type111()
                    secondary_ready = False
                    error_code = "negotiated_child_missing"
                    return SerializerResult(0, 1)
                lease = _IngestChildLease(self.ingest, receiver_generation)
                if not child.own_resource(lease):
                    lease.close()
                    secondary_ready = False
                    error_code = "child_resource_ownership_rejected"
                    return SerializerResult(0, 1)
                self._child_lease = lease
                identity = self.ingest.receiver.stream_identity(111)
                child_generation = child.generation
                if (identity.connection_id != secondary_ids[0] or
                        identity.session_generation != receiver_generation):
                    error_code = "receiver_identity_binding_mismatch"
                    return SerializerResult(0, 1)
                self._identity = ComponentIdentity(
                    self._parent_identity, self._parent_generation or 0,
                    child_generation, secondary_ids[0], receiver_generation,
                    identity.stream_generation,
                    DecoderGenerationIdentity(
                        receiver_generation,
                        self.ingest.receiver.secondary_decoder_generation,
                    ),
                )
                return serializer(candidate)

            model_setup = self.model.handle_setup(
                self._parent_identity, self._parent_generation or 0, request,
                prepare_actual_child,
            )

            child_committed = bool(model_setup.child_committed and secondary_ready)
            if not child_committed:
                if model_setup.child_committed:
                    self.model.teardown_type111(
                        self._parent_identity, self._parent_generation or 0
                    )
                self._child_lease = None
                self._identity = None
            if secondary_ids and not child_committed and error_code is None:
                error_code = model_setup.error_code or "type111_not_committed"
            if primary_ids and not primary_ready and error_code is None:
                error_code = "type110_receiver_setup_failed"
            self._setup_done = True
            return IntegratedSetupResult(
                self._info, model_setup, primary_ready, child_committed,
                self._identity if child_committed else None, error_code,
            )

    def accept_primary(self, timeout: float = 1.0) -> None:
        with self._lock:
            self._require_open()
            if self.ingest.receiver.primary is None:
                raise LabMediaError("type110_listener_not_ready")
            self.ingest.receiver.accept_primary(self._receiver_generation, timeout)

    def accept_type111(self, parent_identity: object, parent_generation: int,
                       stream_connection_id: int, timeout: float = 1.0) -> None:
        with self._lock:
            self._require_child(parent_identity, parent_generation, stream_connection_id)
            self.ingest.accept_type111(timeout)

    def pump_type111(self, parent_identity: object, parent_generation: int,
                     stream_connection_id: int) -> Any:
        with self._lock:
            self._require_child(parent_identity, parent_generation, stream_connection_id)
            outcome = self.ingest.pump_frame()
            if outcome.accepted and outcome.frame is not None:
                identity = self._identity
                assert identity is not None
                bound = outcome.frame
                self._identity = replace(
                    identity,
                    decoder_generation=DecoderGenerationIdentity(
                        self.ingest.receiver.generation,
                        self.ingest.receiver.secondary_decoder_generation,
                    ),
                    display_lease_epoch=bound.lease_epoch,
                    display_lease_generation=bound.lease_generation,
                )
            elif not outcome.accepted or outcome.fault is not None:
                self.model.teardown_type111(
                    parent_identity, parent_generation
                )
                self._child_lease = None
                self._identity = None
            return outcome

    def pump_primary(self) -> bytes:
        with self._lock:
            self._require_open()
            if self.ingest.receiver.primary is None:
                raise LabMediaError("type110_listener_not_ready")
            return self.ingest.receiver.receive_primary_frame(self._receiver_generation)

    def reconcile(self) -> bool:
        with self._lock:
            self._require_open()
            changed = bool(self.ingest.tick())
            if (self._identity is not None and
                    (self.ingest.receiver.secondary is None or
                     self.ingest.coordinator.lease is None)):
                self.model.teardown_type111(
                    self._parent_identity, self._parent_generation or 0
                )
                self._child_lease = None
                self._identity = None
                changed = True
            return changed

    def teardown_type111(self, parent_identity: object, parent_generation: int) -> bool:
        with self._lock:
            self._require_parent(parent_identity, parent_generation)
            if self._identity is None:
                return True
            closed = self.model.teardown_type111(parent_identity, parent_generation)
            self._child_lease = None
            self._identity = None
            return closed

    def close_parent(self, parent_identity: object, parent_generation: int) -> bool:
        with self._lock:
            self._require_parent(parent_identity, parent_generation)
            # Child teardown first routes through its generation-bound resource;
            # then the existing ingest pipeline closes the whole lab session.
            closed = self.model.close_parent(parent_identity, parent_generation)
            self._child_lease = None
            self._identity = None
            self.ingest.disconnect()
            self._closed = True
            return closed

    def residual(self) -> tuple[str, ...]:
        with self._lock:
            residual = list(self.ingest.residual())
            child = self.model.delegator.secondary.lifecycle.current_type111
            if child is not None:
                residual.append(f"model_child:{child.phase.name}")
            if self._identity is not None and self.ingest.receiver.secondary is None:
                residual.append("identity_without_receiver")
            return tuple(residual)

    def _require_open(self) -> None:
        if (self._closed or self._parent_identity is None or
                self._parent_generation is None):
            raise LabMediaError("parent_session_not_active")

    def _require_parent(self, identity: object, generation: int) -> None:
        self._require_open()
        if identity is not self._parent_identity or generation != self._parent_generation:
            raise LabMediaError("parent_identity_or_generation_mismatch")

    def _require_child(self, identity: object, generation: int, stream_id: int) -> None:
        self._require_parent(identity, generation)
        binding = self._identity
        if binding is None:
            raise LabMediaError("type111_child_not_active")
        if stream_id != binding.stream_connection_id:
            raise LabMediaError("stream_connection_id_mismatch")
        if (binding.receiver_session_generation != self._receiver_generation or
                binding.receiver_stream_generation !=
                self.ingest.receiver.stream_identity(111).stream_generation):
            raise LabMediaError("stale_receiver_generation")
        decoder_identity = DecoderGenerationIdentity(
            self.ingest.receiver.generation,
            self.ingest.receiver.secondary_decoder_generation,
        )
        if binding.decoder_generation != decoder_identity:
            raise LabMediaError("stale_decoder_generation")
