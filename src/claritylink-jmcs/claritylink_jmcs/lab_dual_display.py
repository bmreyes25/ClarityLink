"""Integrated, offline-only Type110-parent / Type111-child negotiation model.

This module composes the existing mock stock-first SETUP delegator and
generation-owned Type111 lifecycle. Its mappings are model values, not Honda
wire responses. No Honda receiver, session, Screen, listener, or key is used.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Hashable, Mapping

from .capabilities import CapabilityMode, SecondaryDisplayCapability, host_info
from .session_transport import ControlRequest, TransportError, validate_control_request
from .stock_delegation import (DelegatedSetupResult, DelegationError,
                               StockFirstType111Delegator)
from type111_setup_contract import SerializerResult


class LabModelError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class InfoPolicy(str, Enum):
    DISABLED = "disabled"
    MODEL_ONLY = "model_only"


@dataclass(frozen=True)
class SyntheticReadiness:
    """Explicit laboratory preconditions; these are not Honda readiness proofs."""
    listener_allocator_available: bool = False
    independent_security_owner_available: bool = False
    secondary_display_adapter_available: bool = False

    def __post_init__(self) -> None:
        if any(type(value) is not bool for value in (
            self.listener_allocator_available,
            self.independent_security_owner_available,
            self.secondary_display_adapter_available,
        )):
            raise LabModelError("readiness_values_must_be_boolean")

    @property
    def complete(self) -> bool:
        return (self.listener_allocator_available and
                self.independent_security_owner_available and
                self.secondary_display_adapter_available)


@dataclass(frozen=True)
class ModelInfoResult:
    fields: Mapping[str, Any]
    type111_candidate_present: bool
    reason: str
    evidence: str = "MODEL_ONLY"


@dataclass(frozen=True)
class ModelSetupResult:
    response: Mapping[str, Any]
    requested_type111: bool
    child_committed: bool
    stock_parent_preserved: bool
    serializer_invocations: int
    error_code: str | None
    evidence: str = "MODEL_ONLY"


def _valid_generation(value: object) -> bool:
    return (isinstance(value, int) and not isinstance(value, bool) and
            1 <= value <= (1 << 64) - 1)


def _contains_type111(request: object) -> bool:
    if not isinstance(request, Mapping):
        return False
    streams = request.get("streams")
    return isinstance(streams, (list, tuple)) and any(
        isinstance(item, Mapping) and item.get("type") == 111 for item in streams
    )


class LabDualDisplayModel:
    """Compose /info candidate gating with stock-first SETUP and child teardown.

    ``parent_identity`` is an opaque synthetic token checked by identity, and
    each model instance represents one parent generation. Reconnects create a
    fresh model instance. The listener allocator only reserves a deterministic
    test port; Type111SetupContract still waits for a LISTENING reservation
    before it serializes a child response.
    """

    def __init__(
        self,
        delegator: StockFirstType111Delegator,
        stock_info: Mapping[str, Any],
        stock_setup_response: Mapping[str, Any],
        *,
        secondary_capability: SecondaryDisplayCapability | None = None,
        readiness: SyntheticReadiness = SyntheticReadiness(),
    ) -> None:
        if not isinstance(delegator, StockFirstType111Delegator):
            raise LabModelError("stock_first_delegator_required")
        if (not isinstance(stock_info, Mapping) or
                not isinstance(stock_setup_response, Mapping) or
                not isinstance(readiness, SyntheticReadiness)):
            raise LabModelError("stock_parent_fixtures_required")
        self.delegator = delegator
        self._stock_info = deepcopy(dict(stock_info))
        self._stock_setup_response = deepcopy(dict(stock_setup_response))
        self.secondary_capability = secondary_capability or SecondaryDisplayCapability()
        self.readiness = readiness
        self._parent_identity: Hashable | None = None
        self._generation: int | None = None
        self._info_generation: int | None = None
        self._type111_candidate_present = False
        self._opened = False
        self._closed = False

    def open(self, parent_identity: Hashable, generation: int) -> None:
        if self._opened or self._closed:
            raise LabModelError("model_instance_is_single_use")
        try:
            hash(parent_identity)
        except (TypeError, ValueError) as exc:
            raise LabModelError("invalid_parent_identity") from exc
        if not _valid_generation(generation):
            raise LabModelError("invalid_parent_generation")
        self.delegator.open(generation)
        self._parent_identity = parent_identity
        self._generation = generation
        self._opened = True

    def get_info(
        self,
        parent_identity: Hashable,
        generation: int,
        *,
        policy: InfoPolicy = InfoPolicy.DISABLED,
    ) -> ModelInfoResult:
        self._require_parent(parent_identity, generation)
        if not isinstance(policy, InfoPolicy):
            raise LabModelError("invalid_info_policy")
        stock = deepcopy(self._stock_info)
        stock_displays = stock.get("displays")
        if not isinstance(stock_displays, list) or not stock_displays:
            raise LabModelError("stock_info_displays_invalid")
        self._info_generation = generation
        self._type111_candidate_present = False
        if policy is InfoPolicy.DISABLED:
            return ModelInfoResult(stock, False, "policy_disabled")
        if not self._ready_for_candidate():
            return ModelInfoResult(stock, False, "synthetic_readiness_incomplete")
        if (not self.secondary_capability.enabled or
                self.secondary_capability.mode is not CapabilityMode.SYNTHETIC_LAB):
            return ModelInfoResult(stock, False, "synthetic_profile_not_enabled")
        primary = stock_displays[0]
        if not isinstance(primary, Mapping) or primary.get("type") != 110:
            return ModelInfoResult(stock, False, "stock_primary_descriptor_invalid")
        candidate_capability = SecondaryDisplayCapability(
            width=self.secondary_capability.width,
            height=self.secondary_capability.height,
            fps=self.secondary_capability.fps,
            enabled=True,
            mode=CapabilityMode.SYNTHETIC_LAB,
            physical_width_mm=self.secondary_capability.physical_width_mm,
            physical_height_mm=self.secondary_capability.physical_height_mm,
            main_uuid=str(primary.get("uuid", self.secondary_capability.main_uuid)),
            secondary_uuid=self.secondary_capability.secondary_uuid,
            initial_url=self.secondary_capability.initial_url,
        )
        generated = host_info(candidate_capability)["displays"]
        if not isinstance(generated, list) or len(generated) != 2:
            return ModelInfoResult(stock, False, "synthetic_candidate_invalid")
        candidate = generated[1]
        if not isinstance(candidate, Mapping) or any(
            isinstance(item, Mapping) and
            (item.get("type") == 111 or item.get("uuid") == candidate.get("uuid"))
            for item in stock_displays
        ):
            return ModelInfoResult(stock, False, "candidate_identity_conflict")
        stock["displays"].append(deepcopy(dict(candidate)))
        self._type111_candidate_present = True
        return ModelInfoResult(stock, True, "all_synthetic_readiness_requirements_met")

    def handle_setup(
        self,
        parent_identity: Hashable,
        generation: int,
        request: Mapping[str, Any],
        serializer: Callable[[Mapping[str, Any]], SerializerResult],
    ) -> ModelSetupResult:
        self._require_parent(parent_identity, generation)
        if self._info_generation != generation:
            raise LabModelError("info_required_for_parent_generation")
        if not callable(serializer):
            raise LabModelError("serializer_required")
        requested_type111 = _contains_type111(request)
        try:
            validate_control_request(
                ControlRequest("SETUP", "/session", request, generation), generation
            )
            streams = request.get("streams")
            if not isinstance(streams, (list, tuple)) or len(streams) > 16:
                raise TransportError("setup_stream_count_limit")
        except (TransportError, AttributeError, TypeError) as exc:
            return self._stock_fallback(
                generation, request, serializer, requested_type111,
                getattr(exc, "code", "invalid_setup_request"),
            )
        if requested_type111 and (
            not self._type111_candidate_present or not self._ready_for_candidate()
        ):
            return self._stock_fallback(
                generation, request, serializer, True, "type111_not_advertised_or_ready"
            )
        try:
            delegated: DelegatedSetupResult = self.delegator.handle_setup(
                generation, request, serializer
            )
        except DelegationError as exc:
            # DelegationError currently occurs before the mock stock owner is
            # called. Decline this request without presenting a fixture as an
            # observed stock response or risking a competing second call.
            return ModelSetupResult(
                {}, requested_type111, False,
                self.delegator.primary.active, 0, exc.code,
            )
        return ModelSetupResult(
            deepcopy(dict(delegated.response)), requested_type111,
            delegated.secondary_committed, delegated.primary_preserved,
            delegated.transaction.serializer_invocations, delegated.error_code,
        )

    def teardown_type111(self, parent_identity: Hashable, generation: int) -> bool:
        self._require_parent(parent_identity, generation)
        return self.delegator.teardown_secondary(generation)

    def close_parent(self, parent_identity: Hashable, generation: int) -> bool:
        self._require_parent(parent_identity, generation)
        closed = self.delegator.revoke_session(generation)
        if closed:
            self._closed = True
            self._parent_identity = None
            self._generation = None
            self._info_generation = None
            self._type111_candidate_present = False
        return closed

    def _ready_for_candidate(self) -> bool:
        listener_contract = self.delegator.secondary.listeners
        return bool(
            self._opened and not self._closed and self.delegator.primary.active and
            self.delegator.primary.generation == self._generation and
            listener_contract is not None and self.readiness.complete
        )

    def _require_parent(self, identity: Hashable, generation: int) -> None:
        if (not self._opened or self._closed or self._parent_identity is None or
                not _valid_generation(generation) or
                identity is not self._parent_identity or generation != self._generation or
                not self.delegator.primary.active or
                self.delegator.primary.generation != self._generation):
            raise LabModelError("parent_session_identity_or_generation_mismatch")

    def _stock_fallback(
        self,
        generation: int,
        request: object,
        serializer: Callable[[Mapping[str, Any]], SerializerResult],
        requested_type111: bool,
        error_code: str,
    ) -> ModelSetupResult:
        try:
            response = self.delegator.primary.handle_setup(
                generation, request if isinstance(request, Mapping) else {}
            )
        except DelegationError as exc:
            raise LabModelError(exc.code) from exc
        # The stock owner is authoritative. The constructor fixture is a
        # comparison oracle only; never replace the owner's response with it.
        if response != self._stock_setup_response:
            error_code = "stock_fixture_mismatch"
        try:
            serialized = serializer(deepcopy(response))
        except Exception:
            serialized = None
        serializer_ok = isinstance(serialized, SerializerResult) and serialized.succeeded
        return ModelSetupResult(
            deepcopy(response), requested_type111, False, True, 1,
            error_code if serializer_ok else "stock_serializer_failed",
        )
