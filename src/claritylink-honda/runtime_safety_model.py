"""Offline-only state and invariant checks; deliberately has no target I/O."""
from dataclasses import dataclass
from enum import Enum


class RuntimeState(str, Enum):
    UNATTACHED = "UNATTACHED"
    ATTACH_PENDING = "ATTACH_PENDING"
    ATTACHED = "ATTACHED"
    PREPARED = "PREPARED"
    PATCHED = "PATCHED"
    VERIFYING = "VERIFYING"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    RESTORING = "RESTORING"
    VERIFIED = "VERIFIED"
    DETACHED = "DETACHED"
    ABORTED = "ABORTED"
    UNKNOWN = "UNKNOWN"


_NEXT = {
    RuntimeState.UNATTACHED: {RuntimeState.ATTACH_PENDING, RuntimeState.ABORTED},
    RuntimeState.ATTACH_PENDING: {RuntimeState.ATTACHED, RuntimeState.ABORTED, RuntimeState.UNKNOWN},
    RuntimeState.ATTACHED: {RuntimeState.PREPARED, RuntimeState.ROLLBACK_PENDING, RuntimeState.ABORTED},
    RuntimeState.PREPARED: {RuntimeState.PATCHED, RuntimeState.ROLLBACK_PENDING, RuntimeState.ABORTED},
    RuntimeState.PATCHED: {RuntimeState.VERIFYING, RuntimeState.ROLLBACK_PENDING, RuntimeState.UNKNOWN},
    RuntimeState.VERIFYING: {RuntimeState.ROLLBACK_PENDING, RuntimeState.ABORTED, RuntimeState.UNKNOWN},
    RuntimeState.ROLLBACK_PENDING: {RuntimeState.RESTORING, RuntimeState.UNKNOWN},
    RuntimeState.RESTORING: {RuntimeState.VERIFIED, RuntimeState.UNKNOWN},
    RuntimeState.VERIFIED: {RuntimeState.DETACHED, RuntimeState.UNKNOWN},
    RuntimeState.DETACHED: set(),
    RuntimeState.ABORTED: set(),
    RuntimeState.UNKNOWN: set(),
}


@dataclass
class RuntimeStateMachine:
    state: RuntimeState = RuntimeState.UNATTACHED

    def advance(self, next_state: RuntimeState, *, preconditions_met: bool,
                exit_evidence_complete: bool = True) -> RuntimeState:
        if next_state not in _NEXT[self.state]:
            raise ValueError(f"forbidden transition: {self.state.value}->{next_state.value}")
        if preconditions_met is not True or exit_evidence_complete is not True:
            if self.state in (RuntimeState.PATCHED, RuntimeState.VERIFYING):
                self.state = RuntimeState.ROLLBACK_PENDING
                return self.state
            if self.state in (RuntimeState.ROLLBACK_PENDING, RuntimeState.RESTORING,
                              RuntimeState.VERIFIED, RuntimeState.PATCHED):
                self.state = RuntimeState.UNKNOWN
                return self.state
            self.state = RuntimeState.ABORTED
            return self.state
        self.state = next_state
        return self.state


@dataclass(frozen=True)
class RuntimeSafetyInvariants:
    type110_unchanged: bool
    serializer_calls: int
    stock_return_preserved: bool
    wildcard_bind: bool
    generation_owned_by_transaction: bool
    stale_generation_cleanup_attempted: bool
    rollback_complete: bool
    restoration_complete: bool
    cf_objects_owned_or_borrowed_explicitly: bool
    listener_owned_by_generation: bool
    pointers_validated_before_use: bool
    null_checked_before_dereference: bool


def assert_runtime_invariants(facts: RuntimeSafetyInvariants) -> None:
    if not isinstance(facts, RuntimeSafetyInvariants):
        raise ValueError("invariant evidence type invalid")
    checks = (
        facts.type110_unchanged is True,
        facts.serializer_calls == 1 and not isinstance(facts.serializer_calls, bool),
        facts.stock_return_preserved is True,
        facts.wildcard_bind is False,
        facts.generation_owned_by_transaction is True,
        facts.stale_generation_cleanup_attempted is False,
        facts.rollback_complete is True,
        facts.restoration_complete is True,
        facts.cf_objects_owned_or_borrowed_explicitly is True,
        facts.listener_owned_by_generation is True,
        facts.pointers_validated_before_use is True,
        facts.null_checked_before_dereference is True,
    )
    if not all(checks):
        raise ValueError("runtime safety invariant violated or unproven")
