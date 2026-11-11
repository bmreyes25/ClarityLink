"""Unimplemented boundary required before any Honda-native integration.

The protocols describe ownership and readiness evidence that a future
firmware-specific adapter must obtain from genuine receiver-created objects.
This file contains no Honda binding, hook, credential, port, or implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable


class NativeInfoPolicy(str, Enum):
    DISABLED = "disabled"
    TYPE111_CANDIDATE = "type111_candidate"


@dataclass(frozen=True)
class ParentSessionProof:
    """Opaque proof wrapper supplied only by a verified native adapter."""
    owner_token: object
    generation: int

    def __post_init__(self) -> None:
        if self.owner_token is None or (isinstance(self.generation, bool) or
                                        not isinstance(self.generation, int) or
                                        self.generation < 1):
            raise ValueError("invalid_native_parent_proof")


@dataclass(frozen=True)
class StockInfoResult:
    """Original stock result paired with its verified receiver owner."""
    value: Any
    owner_token: object

    def __post_init__(self) -> None:
        if self.value is None or self.owner_token is None:
            raise ValueError("invalid_native_stock_info_result")


@dataclass(frozen=True)
class ChildReadiness:
    listener_ready: bool
    independent_security_ready: bool
    screen_association_ready: bool

    def __post_init__(self) -> None:
        if any(type(value) is not bool for value in (
            self.listener_ready, self.independent_security_ready,
            self.screen_association_ready,
        )):
            raise ValueError("native_child_readiness_must_be_boolean")

    @property
    def ready(self) -> bool:
        return (self.listener_ready and self.independent_security_ready and
                self.screen_association_ready)


@dataclass(frozen=True)
class NativeType111Lease:
    """Opaque project child handle scoped to one native parent generation."""
    owner_token: object
    generation: int
    opaque_handle: object

    def __post_init__(self) -> None:
        if (self.owner_token is None or isinstance(self.generation, bool) or
                not isinstance(self.generation, int) or self.generation < 1 or
                self.opaque_handle is None):
            raise ValueError("invalid_native_type111_lease")


@runtime_checkable
class HondaNativeReceiverAdapter(Protocol):
    """Future adapter surface; no implementation currently satisfies it.

    An implementation must bind proofs/results to the same opaque owner token,
    preserve the original result on every non-ready/error path, enable
    augmentation only for the explicit TYPE111_CANDIDATE policy, and revoke
    only the exact child lease for that parent generation. The protocol does
    not supply or infer a Honda object, listener, session, Screen, or key.
    """

    def prove_parent_session(self, receiver_context: object) -> ParentSessionProof | None: ...

    def original_info_result(
        self, receiver_context: object, proof: ParentSessionProof
    ) -> StockInfoResult | None: ...

    def owns_stock_info_result(
        self, result: StockInfoResult, proof: ParentSessionProof
    ) -> bool: ...

    def child_readiness(
        self, proof: ParentSessionProof, request: Mapping[str, Any] | None = None
    ) -> ChildReadiness: ...

    def augment_info_candidate(
        self, result: StockInfoResult, proof: ParentSessionProof,
        policy: NativeInfoPolicy,
    ) -> StockInfoResult: ...

    def prepare_type111_child(
        self, proof: ParentSessionProof, request: Mapping[str, Any]
    ) -> NativeType111Lease | None: ...

    def withdraw_type111_child(
        self, proof: ParentSessionProof, lease: NativeType111Lease, reason: str
    ) -> bool: ...

    def invalidate_parent_generation(self, proof: ParentSessionProof) -> None: ...
